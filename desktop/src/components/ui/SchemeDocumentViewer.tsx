import React, { useMemo } from 'react';

type Block =
  | { type: 'title'; text: string }
  | { type: 'section'; text: string }
  | { type: 'paragraph'; text: string }
  | { type: 'bullets'; items: string[] }
  | { type: 'numbered'; items: string[] };

/**
 * Known section header patterns found in scheme documents.
 * Matches ALL-CAPS phrases (3+ words or known headers) optionally followed by a colon.
 */
const SECTION_HEADERS = [
  'SCHEME OVERVIEW', 'SCHEME OBJECTIVES', 'SCHEME OVERVIEW AND OBJECTIVES',
  'OBJECTIVE', 'OBJECTIVES', 'MISSION OVERVIEW', 'VISION AND MISSION',
  'MISSION OBJECTIVES', 'FINANCIAL BENEFITS AND ENTITLEMENTS', 'FINANCIAL BENEFITS',
  'BENEFITS', 'ELIGIBILITY CRITERIA', 'ELIGIBLE BENEFICIARIES',
  'WHO IS EXCLUDED', 'INELIGIBLE CATEGORIES', 'APPLICATION PROCESS',
  'HOW TO APPLY', 'DOCUMENTS REQUIRED', 'REQUIRED DOCUMENTS',
  'IMPORTANT LINKS AND HELPLINE', 'IMPORTANT LINKS', 'HELPLINE',
  'CONTACT INFORMATION', 'KEY FEATURES', 'COMPONENTS',
  'SCHEME COMPONENTS', 'IMPLEMENTATION', 'IMPLEMENTATION FRAMEWORK',
  'FUNDING PATTERN', 'FUNDING', 'GRIEVANCE REDRESSAL',
  'MONITORING AND EVALUATION', 'SKILL TRAINING', 'CREDIT SUPPORT',
  'TOOLKIT INCENTIVE', 'INCENTIVE FOR DIGITAL TRANSACTIONS',
  'MARKETING SUPPORT', 'SOCIAL SECURITY BENEFITS',
  'HOW TO CHECK BENEFICIARY STATUS', 'HOW TO CHECK PAYMENT STATUS',
  'HOW TO CHECK BENEFICIARY/PAYMENT STATUS', 'PAYMENT STATUS',
  'REGISTRATION PROCESS', 'VERIFICATION PROCESS',
  'LIST OF TRADITIONAL TRADES', 'TRADITIONAL TRADES',
  'LOAN DETAILS', 'INTEREST SUBVENTION', 'COVERAGE',
  'PREMIUM DETAILS', 'CLAIM PROCESS', 'SUM INSURED',
  'WAGE RATES', 'EMPLOYMENT GUARANTEE', 'WORKS PERMITTED',
  'SPECIAL PROVISIONS',
];

/** Builds a regex that matches any known header (case-insensitive for flexibility) */
const headerRegex = new RegExp(
  '(?<=\\s|^)(' + SECTION_HEADERS
    .sort((a, b) => b.length - a.length) // longest first to avoid partial matches
    .map(h => h.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
    .join('|') +
  '):?(?=\\s)',
  'g'
);

/**
 * Pre-process raw text: if the document has very few newlines relative to its
 * length, it's a single blob. Insert line breaks before detected section headers
 * and before numbered items so the main parser can handle it.
 */
function normalizeText(raw: string): string {
  // Remove BOM
  let text = raw.replace(/^\uFEFF/, '');

  const lineCount = (text.match(/\n/g) || []).length;
  const isBlob = lineCount < text.length / 500; // e.g. 15000 chars with <30 newlines

  if (!isBlob) return text;

  // Insert newlines before known ALL-CAPS section headers
  text = text.replace(headerRegex, '\n\n$1');

  // Also catch generic ALL-CAPS headers (3+ consecutive capitalized words followed by colon or end)
  // e.g. "ELIGIBLE BENEFICIARIES The scheme..."
  text = text.replace(
    /(?<=\.\s+|^\s*)([A-Z][A-Z /&()-]{15,}?)(?=\s+[A-Z][a-z]|\s*:|\s*\d+\.)/g,
    '\n\n$1\n---'
  );

  // Insert newlines before numbered items: " 1. " " 2. "
  text = text.replace(/(?<=\S)\s+(\d+)\.\s+(?=[A-Z])/g, '\n$1. ');

  // Insert newlines before bullet dashes: " - "
  text = text.replace(/(?<=\S)\s+- (?=[A-Z])/g, '\n- ');

  // Clean up excessive newlines
  text = text.replace(/\n{3,}/g, '\n\n');

  return text.trim();
}

function parseDocument(raw: string): Block[] {
  const normalized = normalizeText(raw);
  const lines = normalized.split('\n');
  const blocks: Block[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const next = lines[i + 1] ?? '';

    // Skip pure separator lines
    if (/^[=\-]{3,}$/.test(line.trim())) { i++; continue; }

    // Skip blank lines
    if (line.trim() === '') { i++; continue; }

    // Title: line followed by ====
    if (/^={3,}$/.test(next.trim())) {
      blocks.push({ type: 'title', text: line.trim() });
      i += 2;
      continue;
    }

    // Section header: line followed by ----
    if (/^-{3,}$/.test(next.trim())) {
      blocks.push({ type: 'section', text: line.trim() });
      i += 2;
      continue;
    }

    // Standalone ALL-CAPS header (no underline needed): 3+ words, all caps, on its own line
    if (
      /^[A-Z][A-Z /&(),-]{8,}:?$/.test(line.trim()) &&
      !/^[=\-]{3,}$/.test(line.trim())
    ) {
      const headerText = line.trim().replace(/:$/, '');
      // First ALL-CAPS line that looks like a title (before any section) → title
      if (blocks.length === 0) {
        blocks.push({ type: 'title', text: headerText });
      } else {
        blocks.push({ type: 'section', text: headerText });
      }
      i++;
      continue;
    }

    // Bullet list: consecutive lines starting with "- "
    if (/^\s*- /.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*- /.test(lines[i])) {
        items.push(lines[i].replace(/^\s*- /, '').trim());
        i++;
      }
      blocks.push({ type: 'bullets', items });
      continue;
    }

    // Numbered list: consecutive lines starting with "N. " or "N) "
    if (/^\s*\d+[.)]\s/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*\d+[.)]\s/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*\d+[.)]\s*/, '').trim());
        i++;
      }
      blocks.push({ type: 'numbered', items });
      continue;
    }

    // Paragraph: collect consecutive non-empty, non-special lines
    {
      let para = '';
      while (
        i < lines.length &&
        lines[i].trim() !== '' &&
        !/^[=\-]{3,}$/.test(lines[i].trim()) &&
        !/^\s*- /.test(lines[i]) &&
        !/^\s*\d+[.)]\s/.test(lines[i]) &&
        !/^[=\-]{3,}$/.test((lines[i + 1] ?? '').trim())
      ) {
        para += (para ? ' ' : '') + lines[i].trim();
        i++;
      }
      if (para) blocks.push({ type: 'paragraph', text: para });
      // If we stopped because next line is a separator underline, the current line is a header — don't skip it
      if (i < lines.length && lines[i]?.trim() !== '' && /^[=\-]{3,}$/.test((lines[i + 1] ?? '').trim())) {
        continue;
      }
    }
  }

  return blocks;
}

/** Detect and linkify URLs and email addresses inside text */
function renderInlineText(text: string): React.ReactNode[] {
  const urlPattern = /(https?:\/\/[^\s,)]+|[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})/g;
  const parts: React.ReactNode[] = [];
  let last = 0;
  let match: RegExpExecArray | null;

  while ((match = urlPattern.exec(text)) !== null) {
    if (match.index > last) parts.push(text.slice(last, match.index));
    const val = match[1];
    if (val.includes('@')) {
      parts.push(<a key={match.index} href={`mailto:${val}`} className="text-neel-500 hover:text-neel-600 dark:text-neel-400 underline underline-offset-2">{val}</a>);
    } else {
      parts.push(<a key={match.index} href={val} target="_blank" rel="noopener noreferrer" className="text-neel-500 hover:text-neel-600 dark:text-neel-400 underline underline-offset-2">{val}</a>);
    }
    last = match.index + val.length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return parts;
}

/** Highlight text inside colons like "Key: value" */
function renderBulletText(text: string): React.ReactNode {
  const colonIdx = text.indexOf(':');
  if (colonIdx > 0 && colonIdx < 60) {
    const label = text.slice(0, colonIdx);
    const rest = text.slice(colonIdx + 1);
    return (
      <>
        <span className="font-semibold text-mitti-800 dark:text-kora-200">{label}:</span>
        {renderInlineText(rest.trimStart())}
      </>
    );
  }
  return renderInlineText(text);
}

export interface FormattedSection {
  heading: string;
  blocks: Array<
    | { type: 'paragraph'; text: string }
    | { type: 'bullets'; items: string[] }
    | { type: 'numbered'; items: string[] }
  >;
}

export interface FormattedDoc {
  title: string;
  sections: FormattedSection[];
}

interface Props {
  /** Raw plain-text document (parsed via regex) */
  content?: string;
  /** Structured LLM-formatted document (preferred when available) */
  formatted?: FormattedDoc;
}

function structuredToBlocks(doc: FormattedDoc): Block[] {
  const blocks: Block[] = [];
  if (doc.title) blocks.push({ type: 'title', text: doc.title });
  for (const section of doc.sections || []) {
    if (section.heading) blocks.push({ type: 'section', text: section.heading });
    for (const block of section.blocks || []) {
      if (block.type === 'paragraph' && block.text) {
        blocks.push({ type: 'paragraph', text: block.text });
      } else if (block.type === 'bullets' && block.items?.length) {
        blocks.push({ type: 'bullets', items: block.items });
      } else if (block.type === 'numbered' && block.items?.length) {
        blocks.push({ type: 'numbered', items: block.items });
      }
    }
  }
  return blocks;
}

const SchemeDocumentViewer: React.FC<Props> = ({ content, formatted }) => {
  const blocks = useMemo(
    () => (formatted ? structuredToBlocks(formatted) : parseDocument(content || '')),
    [content, formatted]
  );

  return (
    <div className="scheme-doc space-y-4">
      {blocks.map((block, idx) => {
        switch (block.type) {
          case 'title':
            return (
              <div key={idx} className="pb-3 mb-2 border-b-2 border-haldi-400/40 dark:border-haldi-500/30">
                <h2 className="text-lg md:text-xl font-bold font-display text-mitti-900 dark:text-kora-100 leading-tight">
                  {block.text}
                </h2>
              </div>
            );

          case 'section':
            return (
              <div key={idx} className="pt-3 first:pt-0">
                <h3 className="text-sm font-bold tracking-wide uppercase text-haldi-700 dark:text-haldi-400 mb-2 flex items-center gap-2">
                  <span className="w-1 h-4 rounded-full bg-gradient-to-b from-haldi-400 to-mitti-400 flex-shrink-0" />
                  {block.text.replace(/[_]/g, ' ')}
                </h3>
              </div>
            );

          case 'paragraph':
            return (
              <p key={idx} className="text-sm text-mitti-700 dark:text-kora-300 leading-relaxed">
                {renderInlineText(block.text)}
              </p>
            );

          case 'bullets':
            return (
              <ul key={idx} className="space-y-1.5 pl-1">
                {block.items.map((item, j) => (
                  <li key={j} className="flex gap-2.5 text-sm text-mitti-700 dark:text-kora-300 leading-relaxed">
                    <span className="mt-2 w-1.5 h-1.5 rounded-full bg-haldi-400 dark:bg-haldi-500 flex-shrink-0" />
                    <span>{renderBulletText(item)}</span>
                  </li>
                ))}
              </ul>
            );

          case 'numbered':
            return (
              <ol key={idx} className="space-y-1.5 pl-1 counter-reset-list">
                {block.items.map((item, j) => (
                  <li key={j} className="flex gap-2.5 text-sm text-mitti-700 dark:text-kora-300 leading-relaxed">
                    <span className="mt-0.5 w-5 h-5 rounded-full bg-mitti-100 dark:bg-night-card text-mitti-600 dark:text-mitti-300 flex-shrink-0 flex items-center justify-center text-xs font-semibold">
                      {j + 1}
                    </span>
                    <span>{renderBulletText(item)}</span>
                  </li>
                ))}
              </ol>
            );

          default:
            return null;
        }
      })}
    </div>
  );
};

export default SchemeDocumentViewer;
