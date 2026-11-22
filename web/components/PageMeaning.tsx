import Link from "next/link";
import { Disclosure } from "./Disclosure";
import { GUIDE_LINK, PAGE_MEANINGS, meaningHref, type PageMeaningId } from "@/lib/guide-copy";

/** The same note, opened from the footer instead of a box at the bottom of the page. */
export function PageMeaning({ page }: { page: PageMeaningId }) {
  const meaning = PAGE_MEANINGS[page];
  return (
    <Disclosure className="rio-page-meaning rio-meaning" title="What this page means">
      {meaning.sentences.map((sentence) => (
        <p key={sentence}>{sentence}</p>
      ))}
      <p>
        <Link href={meaningHref(meaning.section)}>{GUIDE_LINK}</Link>
      </p>
    </Disclosure>
  );
}
