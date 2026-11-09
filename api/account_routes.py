# account_routes.py — sign-up, password, email, delete, and Google.

"""The cookie is set the same way sign-in sets it. A token is not in the JSON.

Delete requires confirm: true. Local delete also requires the email and password,
which is what the Settings form asks for. Hosted delete uses the signed-in
client for the rows and the service role only to remove the auth user.
"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from api.account_flow import (
    change_email_for,
    change_password_for,
    delete_account_for,
    forgot_password,
    google_finish,
    google_start,
    raise_auth,
    reset_password,
    sign_up_hosted,
)
from api.errors import ApiError
from api.identity import (
    clear_session_cookie,
    set_session_cookie,
    sign_in_local,
    sign_out,
)
from api.routes import _principal
from ui.accounts import AccountError, create_account

router = APIRouter(prefix="/auth", tags=["auth"])


class SignUpBody(BaseModel):
    email: str
    password: str
    name: str


class EmailBody(BaseModel):
    email: str


class ResetBody(BaseModel):
    token: str = ""
    password: str = ""


class PasswordBody(BaseModel):
    current_password: str = ""
    new_password: str = ""


class ChangeEmailBody(BaseModel):
    email: str = ""
    password: str = ""


class DeleteAccountBody(BaseModel):
    confirm: bool = False
    email: str = ""
    password: str = ""


def _json(request: Request) -> bool:
    return request.headers.get("x-rio-response", "").strip().lower() == "json"


def _front(request: Request, flag: str) -> str:
    origin = request.app.state.settings.frontend_origin
    return f"{origin}/?google={flag}"


@router.post("/sign-up")
def sign_up(body: SignUpBody, request: Request, response: Response) -> dict:
    directory = request.app.state.directory
    if directory is None:
        try:
            created_email, _seal = create_account(
                request.app.state.accounts_path,
                body.email,
                body.password,
                body.name,
            )
        except AccountError as exc:
            raise_auth(exc)
        try:
            sid, issued, session = sign_in_local(
                request.app,
                request.app.state.accounts_path,
                created_email,
                body.password,
            )
        except AccountError as exc:
            raise_auth(exc)
        set_session_cookie(response, request.app.state.settings, sid, issued)
        return {
            "email": session.get("email") or "",
            "display_name": session.get("display_name") or "",
            "kind": "local",
            "confirm": False,
        }
    outcome = sign_up_hosted(directory, body.email, body.password, body.name)
    if outcome.get("confirm") is True:
        return {"confirm": True, "message": outcome.get("message") or ""}
    set_session_cookie(response, request.app.state.settings, outcome["sid"], outcome["issued"])
    return {
        "email": outcome.get("email") or "",
        "display_name": outcome.get("display_name") or "",
        "kind": "hosted",
        "confirm": False,
    }


@router.post("/forgot-password")
def forgot(body: EmailBody, request: Request) -> dict:
    return forgot_password(request.app.state.directory, body.email)


@router.post("/reset-password")
def reset(body: ResetBody, request: Request) -> dict:
    return reset_password(request.app.state.directory, body.token, body.password)


@router.post("/password")
def password(body: PasswordBody, request: Request) -> dict:
    who = _principal(request)
    return change_password_for(
        request.app,
        request.app.state.directory,
        who,
        body.current_password,
        body.new_password,
    )


@router.post("/email")
def email(body: ChangeEmailBody, request: Request) -> dict:
    who = _principal(request)
    return change_email_for(
        request.app,
        request.app.state.directory,
        who,
        body.password,
        body.email,
    )


@router.post("/delete")
def delete(body: DeleteAccountBody, request: Request, response: Response) -> dict:
    if body.confirm is not True:
        raise ApiError(400, "Confirm to delete this account.")
    who = _principal(request)
    delete_account_for(
        request.app.state.directory,
        who,
        email=body.email,
        password=body.password,
    )
    sign_out(request.app, request.app.state.directory, who.sid)
    clear_session_cookie(response, request.app.state.settings)
    return {"deleted": True}


@router.get("/google")
def google(request: Request) -> dict:
    return google_start(request.app.state.directory)


@router.get("/google/callback")
def google_callback(request: Request, code: str = "", flow: str = ""):
    try:
        outcome = google_finish(request.app.state.directory, code, flow)
    except ApiError:
        if _json(request):
            raise
        return RedirectResponse(_front(request, "error"), status_code=302)
    response_body = {
        "email": outcome.get("email") or "",
        "display_name": outcome.get("display_name") or "",
        "kind": "hosted",
        "redirect_uri": outcome.get("redirect_uri") or "",
    }
    if _json(request):
        from fastapi.responses import JSONResponse

        ready = JSONResponse(response_body)
        set_session_cookie(ready, request.app.state.settings, outcome["sid"], outcome["issued"])
        return ready
    ready = RedirectResponse(_front(request, "connected"), status_code=302)
    set_session_cookie(ready, request.app.state.settings, outcome["sid"], outcome["issued"])
    return ready
