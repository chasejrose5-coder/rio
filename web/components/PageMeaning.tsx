import Link from "next/link";
import { GUIDE_LINK, PAGE_MEANINGS, meaningHref, type PageMeaningId } from "@/lib/guide-copy";

/** A short note at the bottom of a page, with a link into the guide. */
export function PageMeaning({ page }: { page: PageMeaningId }) {
  const meaning = PAGE_MEANINGS[page];
  const headingId = `rio-meaning-${page}`;
  return (
    <section className="rio-meaning" aria-labelledby={headingId}>
      <p className="rio-meaning-kicker" id={headingId}>
        What this means
      </p>
      {meaning.sentences.map((sentence) => (
        <p key={sentence}>{sentence}</p>
      ))}
      <p>
        <Link href={meaningHref(meaning.section)}>{GUIDE_LINK}</Link>
      </p>
    </section>
  );
}
