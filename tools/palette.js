/**
 * palette.js — 繡線色盤（SVG Stitch Editor 專用）
 *
 * 這裡是 colorID 的唯一定義來源：colorID 就是下面陣列的 id（1-16）。
 * 要換成實際的繡線色號，直接改 hex / name 即可，id 請維持 1-16 不要跳號。
 *
 * 用 .js 而非 .json：編輯器是以 file:// 開啟，fetch() 讀本機 JSON 會被
 * 瀏覽器的 CORS 政策擋掉，<script src> 則不受限制。
 */

const STITCH_PALETTE = [
  { id: 1,  name: 'Black',      hex: '#1A1A1A' },
  { id: 2,  name: 'White',      hex: '#FFFFFF' },
  { id: 3,  name: 'Grey',       hex: '#8C8C8C' },
  { id: 4,  name: 'Red',        hex: '#D22B2B' },
  { id: 5,  name: 'Orange',     hex: '#E8710A' },
  { id: 6,  name: 'Gold',       hex: '#E0B01A' },
  { id: 7,  name: 'Green',      hex: '#466d46' },
  { id: 8,  name: 'Forest',     hex: '#1F7A4D' },
  { id: 9,  name: 'Teal',       hex: '#1F9E9E' },
  { id: 10, name: 'Sky',        hex: '#3B9BE0' },
  { id: 11, name: 'Blue',       hex: '#3055ad' },
  { id: 12, name: 'Navy',       hex: '#1E2F6B' },
  { id: 13, name: 'Purple',     hex: '#7B4BC4' },
  { id: 14, name: 'Magenta',    hex: '#873d72' },
  { id: 15, name: 'Pink',       hex: '#EE8FB0' },
  { id: 16, name: 'Brown',      hex: '#a33a3a' }
];

// 選取圖層時的高亮色。刻意和色盤裡的黃(#E0B01A)拉開，避免混淆。
// 高亮是疊在線條上的半透明覆蓋層，底下的真實顏色仍看得見，
// 所以調色時可以即時看到變化。調高 = 高亮更明顯、真實顏色更難辨。
const SELECT_COLOR = '#FFFF00';
const SELECT_OPACITY = 0.3;

function paletteEntry(id) {
  const n = parseInt(id, 10);
  return STITCH_PALETTE.find(c => c.id === n) || STITCH_PALETTE[0];
}

function paletteHex(id) {
  return paletteEntry(id).hex;
}

function hexToRgb(hex) {
  const h = (hex || '').replace('#', '');
  if (h.length !== 6) return null;
  return [parseInt(h.slice(0,2),16), parseInt(h.slice(2,4),16), parseInt(h.slice(4,6),16)];
}

/** 找出色盤中與給定顏色最接近的 id，用於載入 SVG 時自動套色。 */
function nearestPaletteId(hex) {
  const rgb = hexToRgb(hex);
  if (!rgb) return 1;

  let bestId = 1, bestDist = Infinity;
  STITCH_PALETTE.forEach(c => {
    const t = hexToRgb(c.hex);
    const d = (rgb[0]-t[0])**2 + (rgb[1]-t[1])**2 + (rgb[2]-t[2])**2;
    if (d < bestDist) { bestDist = d; bestId = c.id; }
  });
  return bestId;
}

/** 色票上的編號要用黑字還是白字，依底色亮度決定。 */
function paletteTextColor(hex) {
  const rgb = hexToRgb(hex);
  if (!rgb) return '#fff';
  const lum = (rgb[0]*299 + rgb[1]*587 + rgb[2]*114) / 1000;
  return lum > 140 ? '#000' : '#fff';
}
