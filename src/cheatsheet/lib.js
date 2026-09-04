const d = require('docx');
const {
  Paragraph, TextRun, Table, TableRow, TableCell, WidthType, ShadingType,
  BorderStyle, AlignmentType, HeadingLevel, TabStopType
} = d;

// ---------- palette (GitHub-light inspired, readable when printed) ----------
const C = {
  cmd:   'CF222E', // git / cd / New-Item  (first word of a command)
  sub:   '8250DF', // subcommand: status, commit, push
  flag:  '0550AE', // -m  --oneline
  str:   '0A3069', // "quoted text", URLs, paths
  ph:    'BC4C00', // PLACEHOLDER you must replace
  cmt:   '6E7781', // # comments
  plain: '1F2328',
  ref:   '116329', // HEAD, main, origin
  danger:'A40E26',
  h1:    '0B4F6C',
  h2:    '0969DA',
  h3:    '424A53',
};

const PAGE_W = 10080; // 12240 letter - 2 x 1080 margins

const GIT_CONSTS = new Set(['HEAD','ORIG_HEAD','FETCH_HEAD','main','master','origin','.']);
const CMD_WORDS  = new Set(['git','cd','ls','dir','code','notepad','ni','New-Item','Set-Content','Get-Content','gh','clear','cls','winget','md','mkdir','ssh-keygen','echo']);

// ---------- syntax colouring ----------
function tokenize(line) {
  const t = line.trim();
  if (t === '') return [{ text: ' ', color: C.plain }];
  if (t.startsWith('#')) return [{ text: line, color: C.cmt, italics: true }];
  if (t.startsWith('[') ) return [{ text: line, color: C.cmt, italics: true }];
  if (/^(<{7}|={7}|>{7})/.test(t)) return [{ text: line, color: C.danger, bold: true }];

  const out = [];
  const re = /("[^"]*"|'[^']*'|\s+|[^\s]+)/g;
  let m, expectCmd = true, prevWasGit = false;
  while ((m = re.exec(line)) !== null) {
    const tok = m[0];
    if (/^\s+$/.test(tok)) { out.push({ text: tok, color: C.plain }); continue; }

    if (tok === '&&' || tok === ';' || tok === '|' || tok === '||') {
      out.push({ text: tok, color: C.cmd, bold: true });
      expectCmd = true; prevWasGit = false; continue;
    }
    if (tok.startsWith('#')) {                      // trailing comment
      const rest = line.slice(m.index);
      out.push({ text: rest, color: C.cmt, italics: true });
      break;
    }
    if (expectCmd && CMD_WORDS.has(tok)) {
      out.push({ text: tok, color: C.cmd, bold: true });
      prevWasGit = (tok === 'git' || tok === 'gh'); expectCmd = false; continue;
    }
    if (prevWasGit && !tok.startsWith('-')) {
      out.push({ text: tok, color: C.sub, bold: true });
      prevWasGit = false; expectCmd = false; continue;
    }
    expectCmd = false; prevWasGit = false;

    if (tok.startsWith('"') || tok.startsWith("'")) { out.push({ text: tok, color: C.str }); continue; }
    if (tok.startsWith('-'))                        { out.push({ text: tok, color: C.flag }); continue; }
    if (/^<[^>]+>$/.test(tok) || /^[A-Z][A-Z0-9_-]{2,}$/.test(tok) && !GIT_CONSTS.has(tok)) {
      out.push({ text: tok, color: C.ph, bold: true }); continue;
    }
    if (GIT_CONSTS.has(tok) || /^(HEAD~\d+|origin\/\S+)$/.test(tok)) { out.push({ text: tok, color: C.ref }); continue; }
    if (/(https?:\/\/|github\.com|^[A-Za-z]:\\|\\|\/)/.test(tok))    { out.push({ text: tok, color: C.str }); continue; }
    out.push({ text: tok, color: C.plain });
  }
  return out;
}

const MONO = 'Consolas';

function codeParagraph(line, opts = {}) {
  return new Paragraph({
    spacing: { before: 20, after: 20, line: 264 },
    keepLines: true,
    children: tokenize(line).map(p => new TextRun({
      text: p.text, font: MONO, size: 19,
      color: p.color, bold: !!p.bold, italics: !!p.italics,
    })),
    ...opts,
  });
}

// One clean box around a whole snippet (1x1 table = single border, not one per line)
function box(lines, { fill = 'F6F8FA', edge = 'D0D7DE', left = null, label = null } = {}) {
  const kids = [];
  if (label) {
    kids.push(new Paragraph({
      spacing: { before: 0, after: 40 },
      children: [new TextRun({ text: label, bold: true, size: 15, color: C.cmt, allCaps: true, font: 'Segoe UI' })],
    }));
  }
  lines.forEach(l => kids.push(codeParagraph(l)));
  const b = (sz, col) => ({ style: sz ? BorderStyle.SINGLE : BorderStyle.NONE, size: sz, color: col || edge });
  return new Table({
    columnWidths: [PAGE_W],
    width: { size: PAGE_W, type: WidthType.DXA },
    borders: {
      top: b(left ? 0 : 4), bottom: b(left ? 0 : 4),
      right: b(left ? 0 : 4), left: left ? b(24, left) : b(4),
      insideHorizontal: b(0), insideVertical: b(0),
    },
    rows: [new TableRow({
      cantSplit: true,
      children: [new TableCell({
        width: { size: PAGE_W, type: WidthType.DXA },
        shading: { type: ShadingType.CLEAR, color: 'auto', fill },
        margins: { top: 110, bottom: 110, left: 150, right: 150 },
        children: kids,
      })],
    })],
  });
}

function code(lines, label)  { return box(lines, { label }); }
function paste(lines)        { return box(lines, { fill: 'F2F8FF', edge: 'B6D9F5', label: 'Copy this whole block into PowerShell' }); }

// Callouts
function callout(kind, runs) {
  const style = {
    tip:     { fill: 'F1FAF3', edge: '1A7F37', word: 'TIP' },
    note:    { fill: 'F4F8FC', edge: '0969DA', word: 'NOTE' },
    warning: { fill: 'FFF8F0', edge: 'BC4C00', word: 'WARNING' },
    danger:  { fill: 'FFF0F0', edge: 'A40E26', word: 'DANGER' },
  }[kind];
  const kids = [new Paragraph({
    spacing: { before: 0, after: 0 },
    children: [
      new TextRun({ text: style.word + '  ', bold: true, color: style.edge, size: 19, font: 'Segoe UI' }),
      ...toRuns(runs),
    ],
  })];
  const none = { style: BorderStyle.NONE, size: 0, color: 'auto' };
  return new Table({
    columnWidths: [PAGE_W],
    width: { size: PAGE_W, type: WidthType.DXA },
    borders: {
      top: none, bottom: none, right: none,
      left: { style: BorderStyle.SINGLE, size: 24, color: style.edge },
      insideHorizontal: none, insideVertical: none,
    },
    rows: [new TableRow({
      cantSplit: true,
      children: [new TableCell({
        width: { size: PAGE_W, type: WidthType.DXA },
        shading: { type: ShadingType.CLEAR, color: 'auto', fill: style.fill },
        margins: { top: 110, bottom: 110, left: 150, right: 150 },
        children: kids,
      })],
    })],
  });
}

// mini-markup: `code`  **bold**  *italic*
function toRuns(text, base = {}) {
  if (Array.isArray(text)) return text;
  const runs = [];
  const re = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)/g;
  let last = 0, m;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) runs.push(new TextRun({ text: text.slice(last, m.index), ...base }));
    const s = m[0];
    if (s.startsWith('`')) {
      runs.push(new TextRun({
        text: s.slice(1, -1), font: MONO, size: 19, color: C.sub,
        shading: { type: ShadingType.CLEAR, color: 'auto', fill: 'F2EEFB' }, ...base,
      }));
    } else if (s.startsWith('**')) {
      runs.push(new TextRun({ text: s.slice(2, -2), bold: true, ...base }));
    } else {
      runs.push(new TextRun({ text: s.slice(1, -1), italics: true, ...base }));
    }
    last = m.index + s.length;
  }
  if (last < text.length) runs.push(new TextRun({ text: text.slice(last), ...base }));
  return runs;
}

const P  = (text, opts = {}) => new Paragraph({ spacing: { before: 80, after: 80 }, children: toRuns(text), ...opts });
const B  = (text) => new Paragraph({ bullet: { level: 0 }, spacing: { before: 40, after: 40 }, children: toRuns(text) });
const N  = (text) => new Paragraph({ numbering: { reference: 'steps', level: 0 }, spacing: { before: 60, after: 60 }, children: toRuns(text) });
const H1 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_1, pageBreakBefore: true, keepNext: true, children: toRuns(text) });
const H1c= (text) => new Paragraph({ heading: HeadingLevel.HEADING_1, keepNext: true, children: toRuns(text) });
const H2 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_2, keepNext: true, children: toRuns(text) });
const H3 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_3, keepNext: true, children: toRuns(text) });
const SP = (h = 80) => new Paragraph({ spacing: { before: 0, after: h }, children: [] });

// Table helper: rows[0] is the header. widths must sum to PAGE_W.
function grid(widths, rows, { mono = [] } = {}) {
  const edge = { style: BorderStyle.SINGLE, size: 4, color: 'D0D7DE' };
  return new Table({
    columnWidths: widths,
    width: { size: PAGE_W, type: WidthType.DXA },
    borders: { top: edge, bottom: edge, left: edge, right: edge, insideHorizontal: edge, insideVertical: edge },
    rows: rows.map((cells, r) => new TableRow({
      tableHeader: r === 0,
      children: cells.map((cell, i) => new TableCell({
        width: { size: widths[i], type: WidthType.DXA },
        shading: { type: ShadingType.CLEAR, color: 'auto', fill: r === 0 ? 'EDF2F7' : (r % 2 ? 'FFFFFF' : 'FAFBFC') },
        margins: { top: 80, bottom: 80, left: 120, right: 120 },
        children: [ r === 0
          ? new Paragraph({ spacing: { before: 0, after: 0 }, children: [new TextRun({ text: cell, bold: true, size: 19 })] })
          : (mono.includes(i)
              ? codeParagraph(cell, { spacing: { before: 0, after: 0 } })
              : new Paragraph({ spacing: { before: 0, after: 0 }, children: toRuns(cell, { size: 19 }) })) ],
      })),
    })),
  });
}

module.exports = { d, C, PAGE_W, code, paste, box, callout, grid, P, B, N, H1, H1c, H2, H3, SP, toRuns, MONO, codeParagraph };
