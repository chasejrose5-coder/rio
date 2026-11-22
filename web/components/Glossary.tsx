import { GLOSSARY } from "@/lib/glossary";

export function Glossary() {
  return (
    <details className="rio-glossary-words">
      <summary>What the words mean</summary>
      <dl>
        {GLOSSARY.map((item) => (
          <div key={item.term}>
            <dt>{item.term}</dt>
            <dd>{item.meaning}</dd>
          </div>
        ))}
      </dl>
    </details>
  );
}
