# -*- coding: utf-8 -*-

import streamlit as st
import streamlit.components.v1 as components
from PIL import Image
import base64
import io
import json

# --- 常數 ---
CROP_X_PAD = 55
CROP_Y_PAD = 5
SHEET_COLS = 10
SHEET_ROWS = 4

# --- 載入圖片 ---
img = Image.open("ExampleRegular.png")
SHEET_W, SHEET_H = img.size
TILE_W = SHEET_W / SHEET_COLS
TILE_H = SHEET_H / SHEET_ROWS

# --- 座標表 ---
tile_coords: dict[str, tuple[int, int]] = {
    "東": (0, 3), "南": (1, 3), "西": (2, 3), "北": (3, 3),
    "中": (4, 3), "白": (5, 3), "發": (6, 3),
}
for row_idx, suit in enumerate(("m", "p", "s")):
    for i in range(1, 10):
        if i <= 5:
            tile_coords[f"{i}{suit}"] = (i - 1, row_idx)
            if i == 5:
                tile_coords[f"{i}r{suit}"] = (i, row_idx)
        else:
            tile_coords[f"{i}{suit}"] = (i, row_idx)

# --- 牌庫顯示順序（含紅五）---
DISPLAY_ROWS = [
    [f"{i}m" for i in range(1, 10)] + ["5rm"],
    [f"{i}p" for i in range(1, 10)] + ["5rp"],
    [f"{i}s" for i in range(1, 10)] + ["5rs"],
    ["東", "南", "西", "北", "中", "白", "發"],
]

# --- 切圖轉 base64 ---
def tile_to_b64(col: int, row: int) -> str:
    x0, y0 = col * TILE_W, row * TILE_H
    tile = img.crop((
        round(x0 + CROP_X_PAD),
        round(y0 + CROP_Y_PAD),
        round(x0 + TILE_W - CROP_X_PAD),
        round(y0 + TILE_H - CROP_Y_PAD),
    ))
    buf = io.BytesIO()
    tile.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()

all_names = {n for row in DISPLAY_ROWS for n in row}
tile_b64 = {
    name: tile_to_b64(col, row)
    for name, (col, row) in tile_coords.items()
    if name in all_names
}

tiles_data = [
    [{"name": name, "src": f"data:image/png;base64,{tile_b64[name]}"}
     for name in row]
    for row in DISPLAY_ROWS
]
tiles_json = json.dumps(tiles_data, ensure_ascii=False)

# ===========================================================================
# 自包含 HTML 元件（牌庫 + 手牌 + 副露 + 役種判定，全部由 JavaScript 處理）
# ===========================================================================
html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: sans-serif; background: #f2f2f2; padding: 20px 12px 12px; }}
  h3 {{ font-size: 13px; color: #444; margin-bottom: 7px; }}

  /* ── 牌庫 ── */
  .picker-area {{
    background: #dcdcdc; border-radius: 8px;
    padding: 10px 12px 12px; margin-bottom: 10px;
  }}
  .tile-row {{ display: flex; gap: 4px; margin-bottom: 5px; }}
  .tile-row:last-child {{ margin-bottom: 0; }}
  .tile {{
    cursor: pointer; border-radius: 4px; border: 2px solid transparent;
    line-height: 0; transition: transform 0.15s ease, border-color 0.1s;
  }}
  .tile:hover {{ transform: translateY(-8px); border-color: #4a90e2; }}
  .tile.full {{ opacity: 0.35; cursor: not-allowed; pointer-events: none; }}
  .tile img {{ width: 46px; display: block; }}

  /* ── 模式切換 ── */
  .mode-toggle {{
    display: flex; gap: 8px; align-items: center; margin-bottom: 10px;
  }}
  .mode-btn {{
    padding: 5px 22px; border: 2px solid #aaa; border-radius: 20px;
    background: #fff; cursor: pointer; font-size: 13px; font-weight: bold;
    color: #666; transition: all 0.15s;
  }}
  .mode-btn.hand-on  {{ background: #4a90e2; border-color: #4a90e2; color: #fff; }}
  .mode-btn.fuuro-on {{ background: #c8650a; border-color: #c8650a; color: #fff; }}
  .mode-hint {{ font-size: 11px; color: #999; }}

  /* ── 手牌 / 副露 共用框 ── */
  .hand-area, .fuuro-area {{
    border-radius: 8px; padding: 10px 6px 10px; margin-bottom: 10px;
    border: 2px solid transparent; transition: border-color 0.2s;
  }}
  .hand-area  {{ background: #cfe3bc; }}
  .fuuro-area {{ background: #f0ddc4; }}
  .hand-area.area-on  {{ border-color: #4a90e2; }}
  .fuuro-area.area-on {{ border-color: #c8650a; }}

  .area-header {{
    display: flex; justify-content: space-between; align-items: center; margin-bottom: 7px;
  }}
  .count {{ font-size: 12px; color: #555; }}
  .btn-clear {{
    font-size: 12px; padding: 2px 10px; border: 1px solid #aaa;
    border-radius: 4px; background: #fff; cursor: pointer;
  }}
  .btn-clear:hover {{ background: #fdd; border-color: #c00; }}

  /* 牌列（固定一行）*/
  .tile-row-display {{
    display: flex; flex-wrap: nowrap; gap: 2px;
    min-height: 54px; align-items: flex-end; overflow-x: visible;
  }}
  .placed-tile {{
    cursor: pointer; border-radius: 4px; border: 2px solid transparent;
    line-height: 0; flex-shrink: 0; transition: transform 0.12s ease, border-color 0.1s;
  }}
  .placed-tile.is-hand:hover  {{ transform: translateY(-6px); border-color: #e05555; }}
  .placed-tile.is-fuuro:hover {{ transform: translateY(-6px); border-color: #c8650a; }}
  .placed-tile img {{ width: 42px; display: block; }}

  .hint      {{ color: #999; font-size: 12px; line-height: 54px; white-space: nowrap; }}
  .full-warn {{ color: #b00; font-size: 12px; margin-top: 4px; }}

  /* ── 最後一張手牌 ── */
  .hand-sep {{
    width: 2px; flex-shrink: 0; align-self: stretch;
    border-left: 2px dashed #999; margin: 4px 6px;
  }}
  .last-tile-wrap {{
    display: flex; flex-direction: column; align-items: center; flex-shrink: 0;
  }}
  .last-tile-label {{
    font-size: 10px; color: #fff; background: #888;
    border-radius: 3px; padding: 1px 5px; margin-bottom: 3px;
    white-space: nowrap; letter-spacing: 0.5px;
  }}
  .warn-msg  {{
    display: none; color: #7a4800; font-size: 12px; background: #fff3cd;
    border: 1px solid #ffc107; border-radius: 4px; padding: 4px 10px; margin-top: 5px;
  }}

  /* ── 場風／自風選擇器 ── */
  .wind-selector {{
    background: #e8e8e8; border-radius: 8px;
    padding: 8px 12px; margin-bottom: 10px;
    display: flex; flex-direction: column; gap: 6px;
  }}
  .wind-row {{ display: flex; align-items: center; gap: 6px; }}
  .wind-label {{ font-size: 12px; color: #555; font-weight: bold; width: 32px; flex-shrink: 0; }}
  .wind-btn {{
    padding: 3px 14px; border: 2px solid #bbb; border-radius: 14px;
    background: #fff; cursor: pointer; font-size: 13px; color: #555;
    transition: all 0.12s;
  }}
  .wind-btn:hover {{ border-color: #888; }}
  .wind-btn.rw-on {{ background: #2e7d32; border-color: #2e7d32; color: #fff; }}
  .wind-btn.sw-on {{ background: #1565c0; border-color: #1565c0; color: #fff; }}
  .wind-btn.both-on {{ background: #6a1b9a; border-color: #6a1b9a; color: #fff; }}
  .wind-legend {{ font-size: 11px; color: #999; margin-left: 4px; }}
  .win-btn {{
    padding: 3px 18px; border: 2px solid #bbb; border-radius: 14px;
    background: #fff; cursor: pointer; font-size: 13px; color: #555;
    transition: all 0.12s;
  }}
  .win-btn:hover {{ border-color: #888; }}
  .win-btn.tsumo-on {{ background: #c62828; border-color: #c62828; color: #fff; }}
  .win-btn.ron-on   {{ background: #37474f; border-color: #37474f; color: #fff; }}

  /* ── 判定結果 ── */
  .result-area {{
    border-radius: 8px; padding: 10px 14px; font-size: 13px;
    line-height: 1.8; display: none;
  }}
  .result-win  {{ background: #e8f5e9; border: 1px solid #81c784; color: #1b5e20; }}
  .result-lose {{ background: #fce4ec; border: 1px solid #e57373; color: #880e4f; }}
  .yaku-chips  {{ margin-top: 5px; }}
  .yaku-item {{
    display: inline-block; background: #fff; border: 1px solid #aed581;
    border-radius: 12px; padding: 1px 10px; margin: 2px 3px;
    font-size: 12px; color: #33691e;
  }}
  .note {{ font-size: 11px; color: #888; margin-top: 6px; }}
  .score-line {{ margin-top: 8px; font-size: 14px; font-weight: bold; color: #1b5e20; }}
  .han-fu     {{ font-size: 12px; color: #388e3c; margin-top: 2px; }}
  .dealer-btn {{
    padding: 3px 14px; border: 2px solid #bbb; border-radius: 14px;
    background: #fff; cursor: pointer; font-size: 13px; color: #555;
    transition: all 0.12s;
  }}
  .dealer-btn:hover {{ border-color: #888; }}
  .dealer-btn.dealer-on {{ background: #e65100; border-color: #e65100; color: #fff; }}
  .win-btn.riichi-on  {{ background: #880e4f; border-color: #880e4f; color: #fff; }}
  /* ── 寶牌區 ── */
  .mode-btn.dora-on {{ background: #f57f17; border-color: #f57f17; color: #fff; }}
  .dora-area {{
    background: #fff8e1; border: 1px solid #ffe082; border-radius: 8px;
    padding: 8px 12px; margin-bottom: 10px; display: none;
  }}
  .dora-area.area-on {{ display: block; }}
  .dora-pair  {{ display: inline-flex; flex-direction: column; align-items: center; margin: 2px 6px; }}
  .dora-arrow {{ font-size: 10px; color: #e65100; font-weight: bold; }}
  .is-dora    {{ border-color: #f57f17 !important; }}
  /* ── 文字輸入區 ── */
  .text-input-area {{
    background: #f0f4f8; border: 1px solid #cfd8dc; border-radius: 8px;
    padding: 8px 12px; margin-bottom: 10px;
  }}
  .text-input-row {{ display: flex; gap: 6px; align-items: center; }}
  .text-input-row input {{
    flex: 1; padding: 5px 10px; border: 1px solid #b0bec5; border-radius: 6px;
    font-size: 13px; font-family: monospace;
  }}
  .text-input-row input::placeholder {{ color: #aaa; font-size: 11px; }}
  .parse-btn {{
    padding: 5px 12px; background: #1565c0; color: #fff;
    border: none; border-radius: 6px; cursor: pointer; font-size: 12px; white-space: nowrap;
  }}
  .parse-btn:hover {{ background: #0d47a1; }}
  .input-hint {{ font-size: 11px; color: #78909c; margin-top: 4px; }}
  /* ── 聽牌顯示 ── */
  .result-tenpai {{ background: #e3f2fd; border: 1px solid #64b5f6; color: #0d47a1; }}
  .wait-grid {{ display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0; }}
  .wait-item {{
    display: flex; flex-direction: column; align-items: center; gap: 2px;
    background: rgba(255,255,255,0.65); border-radius: 6px; padding: 4px 5px; min-width: 46px;
  }}
  .wait-han-fu {{ font-size: 10px; color: #0d47a1; font-weight: bold; text-align: center; white-space: nowrap; }}
  .wait-pts    {{ font-size: 10px; color: #1565c0; text-align: center; white-space: nowrap; }}
  .input-warn {{ font-size: 11px; color: #c62828; margin-top: 4px; display: none; }}
</style>
</head>
<body>

<div class="picker-area">
  <h3>牌庫 — 點擊加牌，懸停浮起</h3>
  <div id="picker"></div>
</div>

<div class="wind-selector">
  <div class="wind-row">
    <span class="wind-label">場風</span>
    <button class="wind-btn rw-on" id="rw-東" onclick="setRoundWind('東')">東</button>
    <button class="wind-btn"       id="rw-南" onclick="setRoundWind('南')">南</button>
    <button class="wind-btn"       id="rw-西" onclick="setRoundWind('西')">西</button>
    <button class="wind-btn"       id="rw-北" onclick="setRoundWind('北')">北</button>
    <span class="wind-legend">綠色</span>
  </div>
  <div class="wind-row">
    <span class="wind-label">自風</span>
    <button class="wind-btn sw-on" id="sw-東" onclick="setSeatWind('東')">東</button>
    <button class="wind-btn"       id="sw-南" onclick="setSeatWind('南')">南</button>
    <button class="wind-btn"       id="sw-西" onclick="setSeatWind('西')">西</button>
    <button class="wind-btn"       id="sw-北" onclick="setSeatWind('北')">北</button>
    <span class="wind-legend">藍色，兩者相同時紫色</span>
  </div>
  <div class="wind-row">
    <span class="wind-label">和牌</span>
    <button class="win-btn ron-on" id="btn-ron"   onclick="setWinType(false)">榮和</button>
    <button class="win-btn"        id="btn-tsumo" onclick="setWinType(true)">自摸</button>
  </div>
  <div class="wind-row">
    <span class="wind-label">身份</span>
    <button class="dealer-btn dealer-on" id="btn-ko"  onclick="setDealer(false)">子家</button>
    <button class="dealer-btn"           id="btn-oya" onclick="setDealer(true)">親家</button>
  </div>
  <div class="wind-row">
    <span class="wind-label">立直</span>
    <button class="win-btn" id="btn-riichi" onclick="setRiichi(!isRiichi)">未宣告</button>
    <span class="wind-legend">門前限定，宣告後 +1 翻</span>
  </div>
</div>

<div class="mode-toggle">
  <button class="mode-btn hand-on" id="btn-hand"  onclick="setMode('hand')">手牌</button>
  <button class="mode-btn"         id="btn-fuuro" onclick="setMode('fuuro')">副露</button>
  <button class="mode-btn"         id="btn-dora"  onclick="setMode('dora')">寶牌</button>
  <span class="mode-hint">Tab 鍵切換</span>
</div>

<div class="text-input-area">
  <div class="text-input-row">
    <input type="text" id="tile-input"
      placeholder="輸入牌面，Enter 加入 — 例：123m456p789s東東白  （0m/0p/0s = 紅五）" />
    <button class="parse-btn" onclick="parseTileInput()">加入</button>
  </div>
  <div class="input-hint">數牌：數字＋m/p/s，如 <b>456p</b>；字牌：直接輸入 <b>東南西北白發中</b>；紅五：<b>0m 0p 0s</b>（或 5rm 5rp 5rs）；加入至目前選擇的模式（手牌／副露／寶牌）</div>
  <div class="input-warn" id="input-warn"></div>
</div>

<div class="hand-area area-on" id="hand-area">
  <div class="area-header">
    <h3>手牌 — 點擊移除</h3>
    <span>
      <span class="count" id="count">0 / 14</span>
      &nbsp;
      <button class="btn-clear" onclick="clearArea('hand')">清空</button>
    </span>
  </div>
  <div class="tile-row-display" id="hand"></div>
  <div class="full-warn" id="full-warn" style="display:none">手牌已滿（14 張）</div>
  <div class="warn-msg" id="warn-msg"></div>
</div>

<div class="fuuro-area" id="fuuro-area">
  <div class="area-header">
    <h3>副露 — 點擊移除</h3>
    <span>
      <span class="count" id="fuuro-count">0 張</span>
      &nbsp;
      <button class="btn-clear" onclick="clearArea('fuuro')">清空</button>
    </span>
  </div>
  <div class="tile-row-display" id="fuuro"></div>
</div>

<div class="dora-area" id="dora-area">
  <div class="area-header">
    <h3>寶牌指示牌 — 點擊移除（下方為對應寶牌）</h3>
    <span>
      <span class="count" id="dora-count">0 / 8</span>
      &nbsp;
      <button class="btn-clear" onclick="clearArea('dora')">清空</button>
    </span>
  </div>
  <div class="tile-row-display" id="dora-display"></div>
</div>

<div class="result-area" id="result-area"></div>

<script>
// ═══════════════════════════════════════════════════
// 日麻役種判定（JavaScript）
// ═══════════════════════════════════════════════════

const HONORS = new Set(['東','南','西','北','中','白','發']);
const KOKUSHI_SET = new Set(['1m','9m','1p','9p','1s','9s','東','南','西','北','中','白','發']);
const GREEN_SET   = new Set(['2s','3s','4s','6s','8s','發']);

function norm(t)     {{ return t.replace('r',''); }}
function isHonor(t)  {{ return HONORS.has(t); }}
function tileNum(t)  {{ return isHonor(t) ? 0 : parseInt(t[0]); }}
function tileSuit(t) {{ return isHonor(t) ? 'z' : t[t.length-1]; }}

function handToCounts(arr) {{
  const c = {{}};
  for (const t of arr) {{ const k = norm(t); c[k] = (c[k]||0)+1; }}
  return c;
}}

const HONOR_ORD = {{'東':0,'南':1,'西':2,'北':3,'中':4,'白':5,'發':6}};
const SUIT_ORD  = {{'m':0,'p':1,'s':2,'z':3}};

function sortedTileList(counts) {{
  const tiles = [];
  for (const [k,v] of Object.entries(counts)) for (let i=0;i<v;i++) tiles.push(k);
  tiles.sort((a,b) => {{
    const sa=tileSuit(a), sb=tileSuit(b);
    if (sa!==sb) return SUIT_ORD[sa]-SUIT_ORD[sb];
    if (isHonor(a)&&isHonor(b)) return HONOR_ORD[a]-HONOR_ORD[b];
    return tileNum(a)-tileNum(b);
  }});
  return tiles;
}}

function tryDecompose(counts) {{
  const tiles = sortedTileList(counts);
  if (tiles.length === 0) return {{sequences:[], triplets:[]}};
  const t = tiles[0], c = {{...counts}};
  if (c[t] >= 3) {{
    const c2={{...c}}; c2[t]-=3; if(!c2[t]) delete c2[t];
    const res=tryDecompose(c2);
    if (res) return {{sequences:res.sequences, triplets:[t,...res.triplets]}};
  }}
  if (!isHonor(t) && tileNum(t) <= 7) {{
    const suit=tileSuit(t), n=tileNum(t);
    const t2=`${{n+1}}${{suit}}`, t3=`${{n+2}}${{suit}}`;
    if (c[t2]>=1 && c[t3]>=1) {{
      const c2={{...c}};
      c2[t]--;if(!c2[t])delete c2[t]; c2[t2]--;if(!c2[t2])delete c2[t2]; c2[t3]--;if(!c2[t3])delete c2[t3];
      const res=tryDecompose(c2);
      if (res) return {{sequences:[[t,t2,t3],...res.sequences], triplets:res.triplets}};
    }}
  }}
  return null;
}}

function getDecomposition(counts) {{
  const seen = new Set();
  for (const t of sortedTileList(counts)) {{
    if (seen.has(t)) continue; seen.add(t);
    if ((counts[t]||0) < 2) continue;
    const c2={{...counts}}; c2[t]-=2; if(!c2[t]) delete c2[t];
    const res=tryDecompose(c2);
    if (res) return {{...res, pair:t}};
  }}
  return null;
}}

function isKokushi(counts) {{
  const present=[...KOKUSHI_SET].filter(t=>counts[t]);
  if (present.length<13) return false;
  return [...KOKUSHI_SET].some(t=>(counts[t]||0)>=2);
}}
function isChiitoitsu(counts) {{
  const vals=Object.values(counts);
  return vals.reduce((s,v)=>s+v,0)===14 && vals.length===7 && vals.every(v=>v===2);
}}

// 判斷和牌張是否形成兩面聽
function checkRyamen(sequences, winNorm) {{
  for (const seq of sequences) {{
    if (!seq.includes(winNorm)) continue;
    const wn=tileNum(winNorm);
    const nums=seq.map(t=>tileNum(t)).sort((a,b)=>a-b);
    const [a,,c]=nums;
    if (wn===nums[1]) continue;        // 嵌張（中間補）
    if (wn===a && c<=8) return true;   // 兩面（左補，右可延伸）
    if (wn===c && a>=2) return true;   // 兩面（右補，左可延伸）
  }}
  return false;
}}

function checkYaku(handNames, winNorm) {{
  const counts=handToCounts(handNames), yaku=[];
  if (isKokushi(counts)) {{
    const r=['國士無雙 (役滿)'];
    if (isTsumo) r.unshift('門清自摸 (1翻)');
    return r;
  }}
  if (isChiitoitsu(counts)) {{
    if (isTsumo) yaku.push('門清自摸 (1翻)');
    yaku.push('七對子 (2翻)');
    const allN=handNames.map(t=>norm(t));
    const suits=new Set(allN.filter(t=>!isHonor(t)).map(t=>tileSuit(t)));
    const hasH=allN.some(t=>isHonor(t));
    if (!hasH&&suits.size===1) yaku.push(isTsumo?'清一色 (6翻)':'清一色 (5翻)');
    else if (suits.size===1&&hasH) yaku.push(isTsumo?'混一色 (3翻)':'混一色 (2翻)');
    return yaku;
  }}
  const decomp=getDecomposition(counts);
  if (!decomp) return [];
  if (isTsumo) yaku.push('門清自摸 (1翻)');
  const {{sequences,triplets,pair}}=decomp;
  const allN=handNames.map(t=>norm(t));
  const suits=new Set(allN.filter(t=>!isHonor(t)).map(t=>tileSuit(t)));
  const hasH=allN.some(t=>isHonor(t));
  const hasT=allN.some(t=>!isHonor(t)&&(tileNum(t)===1||tileNum(t)===9));
  // 平和：4順子 ＋ 非役牌雀頭 ＋ 和牌張形成兩面聽
  if (sequences.length===4) {{
    const pairYaku=['中','白','發'].includes(pair)||pair===roundWind||pair===seatWind;
    if (!pairYaku && checkRyamen(sequences, winNorm)) yaku.push('平和 (1翻)');
  }}
  if (!hasH&&!hasT) yaku.push('斷幺九 (1翻)');
  const seqKeys=sequences.map(s=>s.join(','));
  const seqCnt={{}};seqKeys.forEach(k=>{{seqCnt[k]=(seqCnt[k]||0)+1;}});
  const pOS=Object.values(seqCnt).reduce((s,v)=>s+Math.floor(v/2),0);
  if (pOS===2) yaku.push('二盃口 (3翻)'); else if (pOS===1) yaku.push('一盃口 (1翻)');
  const tripNums=triplets.filter(t=>!isHonor(t)).map(t=>{{return{{n:tileNum(t),s:tileSuit(t)}}}});
  for (const n of new Set(tripNums.map(x=>x.n))) {{
    const s=new Set(tripNums.filter(x=>x.n===n).map(x=>x.s));
    if (s.has('m')&&s.has('p')&&s.has('s')){{yaku.push('三色同刻 (2翻)');break;}}
  }}
  const seqNums=sequences.map(s=>{{return{{n:tileNum(s[0]),s:tileSuit(s[0])}}}});
  for (const n of new Set(seqNums.map(x=>x.n))) {{
    const s=new Set(seqNums.filter(x=>x.n===n).map(x=>x.s));
    if (s.has('m')&&s.has('p')&&s.has('s')){{yaku.push('三色同順 (2翻)');break;}}
  }}
  for (const suit of ['m','p','s']) {{
    const starts=new Set(seqNums.filter(x=>x.s===suit).map(x=>x.n));
    if ([1,4,7].every(n=>starts.has(n))){{yaku.push('一氣通貫 (2翻)');break;}}
  }}
  // 暗刻系：榮和補完刻子者不算暗刻，補完雀頭（單騎/雙碰）則全算暗刻
  const winIsPair=(pair===winNorm);
  const ankouCount=(isTsumo||winIsPair)
    ? triplets.length
    : triplets.filter(t=>t!==winNorm).length;
  if (sequences.length===0) yaku.push('對對和 (2翻)');
  if (triplets.length===4&&ankouCount===4) {{
    yaku.push((!isTsumo&&winIsPair)?'四暗刻単騎 (役滿)':'四暗刻 (役滿)');
  }} else if (triplets.length>=3&&ankouCount>=3) {{
    yaku.push('三暗刻 (2翻)');
  }}
  if (allN.every(t=>isHonor(t)||tileNum(t)===1||tileNum(t)===9)) yaku.push('混老頭 (2翻)');
  if (!hasH&&allN.every(t=>tileNum(t)===1||tileNum(t)===9)) yaku.push('清老頭 (役滿)');
  const drT=triplets.filter(t=>['中','白','發'].includes(t)).length;
  const drP=['中','白','發'].includes(pair);
  if (drT===3) yaku.push('大三元 (役滿)'); else if (drT===2&&drP) yaku.push('小三元 (2翻)');
  if (!hasH&&suits.size===1) yaku.push(isTsumo?'清一色 (6翻)':'清一色 (5翻)');
  else if (suits.size===1&&hasH) yaku.push(isTsumo?'混一色 (3翻)':'混一色 (2翻)');
  if (suits.size===0) yaku.push('字一色 (役滿)');
  if (allN.every(t=>GREEN_SET.has(t))) yaku.push('緑一色 (役滿)');
  for (const suit of ['m','p','s']) {{
    const st=allN.filter(t=>tileSuit(t)===suit);
    if (st.length===14) {{
      const c={{}};st.forEach(t=>{{c[t]=(c[t]||0)+1;}});
      const base={{}};base[`1${{suit}}`]=3;base[`9${{suit}}`]=3;
      for(let n=2;n<=8;n++) base[`${{n}}${{suit}}`]=1;
      if (Object.entries(base).every(([k,v])=>(c[k]||0)>=v)) yaku.push('九蓮寶燈 (役滿)');
    }}
  }}
  for (const d of ['白','發','中']) if (triplets.includes(d)) yaku.push(`役牌：${{d}} (1翻)`);
  for (const w of ['東','南','西','北']) {{
    if (triplets.includes(w)) {{
      const fan=(w===roundWind?1:0)+(w===seatWind?1:0);
      if (fan>0) yaku.push(`役牌：${{w}} (${{fan}}翻)`);
    }}
  }}
  return yaku;
}}

function checkYakuOpen(handNames, fuuroNames, winNorm) {{
  const allNames=[...handNames,...fuuroNames];
  const counts=handToCounts(allNames), yaku=[];
  const decomp=getDecomposition(counts);
  if (!decomp) return [];
  const {{sequences,triplets,pair}}=decomp;
  const allN=allNames.map(t=>norm(t));
  const suits=new Set(allN.filter(t=>!isHonor(t)).map(t=>tileSuit(t)));
  const hasH=allN.some(t=>isHonor(t));
  const hasT=allN.some(t=>!isHonor(t)&&(tileNum(t)===1||tileNum(t)===9));
  if (!hasH&&!hasT) yaku.push('斷幺九 (1翻)');
  const tripNums=triplets.filter(t=>!isHonor(t)).map(t=>{{return{{n:tileNum(t),s:tileSuit(t)}}}});
  for (const n of new Set(tripNums.map(x=>x.n))) {{
    const s=new Set(tripNums.filter(x=>x.n===n).map(x=>x.s));
    if (s.has('m')&&s.has('p')&&s.has('s')){{yaku.push('三色同刻 (2翻)');break;}}
  }}
  const seqNums=sequences.map(s=>{{return{{n:tileNum(s[0]),s:tileSuit(s[0])}}}});
  for (const n of new Set(seqNums.map(x=>x.n))) {{
    const s=new Set(seqNums.filter(x=>x.n===n).map(x=>x.s));
    if (s.has('m')&&s.has('p')&&s.has('s')){{yaku.push('三色同順 (1翻)');break;}}
  }}
  for (const suit of ['m','p','s']) {{
    const starts=new Set(seqNums.filter(x=>x.s===suit).map(x=>x.n));
    if ([1,4,7].every(n=>starts.has(n))){{yaku.push('一氣通貫 (1翻)');break;}}
  }}
  if (sequences.length===0) yaku.push('對對和 (2翻)');
  // 三暗刻：只計算手牌中形成的閉刻；榮和時補完刻子者不算暗刻
  const hc=handToCounts(handNames);
  const closedTrips=triplets.filter(t=>(hc[t]||0)>=3);
  const ankouO=(isTsumo||!closedTrips.includes(winNorm))
    ? closedTrips.length
    : closedTrips.length-1;
  if (ankouO>=3) yaku.push('三暗刻 (2翻)');
  if (allN.every(t=>isHonor(t)||tileNum(t)===1||tileNum(t)===9)) yaku.push('混老頭 (2翻)');
  if (!hasH&&allN.every(t=>tileNum(t)===1||tileNum(t)===9)) yaku.push('清老頭 (役滿)');
  const drT=triplets.filter(t=>['中','白','發'].includes(t)).length;
  const drP=['中','白','發'].includes(pair);
  if (drT===3) yaku.push('大三元 (役滿)'); else if (drT===2&&drP) yaku.push('小三元 (2翻)');
  if (!hasH&&suits.size===1) yaku.push('清一色 (5翻)');
  else if (suits.size===1&&hasH) yaku.push('混一色 (2翻)');
  if (suits.size===0) yaku.push('字一色 (役滿)');
  if (allN.every(t=>GREEN_SET.has(t))) yaku.push('緑一色 (役滿)');
  for (const d of ['白','發','中']) if (triplets.includes(d)) yaku.push(`役牌：${{d}} (1翻)`);
  for (const w of ['東','南','西','北']) {{
    if (triplets.includes(w)) {{
      const fan=(w===roundWind?1:0)+(w===seatWind?1:0);
      if (fan>0) yaku.push(`役牌：${{w}} (${{fan}}翻)`);
    }}
  }}
  return yaku;
}}

// ═══════════════════════════════════════════════════
// UI 狀態
// ═══════════════════════════════════════════════════

const rows = {tiles_json};
let hand      = [];
let fuuro     = [];
let mode      = 'hand';   // 'hand' | 'fuuro'
let roundWind = '東';
let seatWind  = '東';

function updateWindButtons() {{
  ['東','南','西','北'].forEach(w => {{
    const isR=w===roundWind, isS=w===seatWind;
    const rb=document.getElementById('rw-'+w), sb=document.getElementById('sw-'+w);
    rb.className='wind-btn'+(isR?(isS?' both-on':' rw-on'):'');
    sb.className='wind-btn'+(isS?(isR?' both-on':' sw-on'):'');
  }});
}}
function setRoundWind(w) {{
  roundWind=w; updateWindButtons(); checkAndShowResult();
}}
function setSeatWind(w) {{
  seatWind=w; updateWindButtons(); checkAndShowResult();
}}

let isTsumo = false;
function setWinType(tsumo) {{
  isTsumo=tsumo;
  document.getElementById('btn-ron').className  ='win-btn'+(!tsumo?' ron-on':'');
  document.getElementById('btn-tsumo').className='win-btn'+(tsumo?' tsumo-on':'');
  checkAndShowResult();
}}

let isDealer = false;
function setDealer(d) {{
  isDealer=d;
  document.getElementById('btn-ko').className ='dealer-btn'+(d?'':' dealer-on');
  document.getElementById('btn-oya').className='dealer-btn'+(d?' dealer-on':'');
  checkAndShowResult();
}}

let isRiichi = false;
function setRiichi(r) {{
  isRiichi=r;
  document.getElementById('btn-riichi').className='win-btn'+(r?' riichi-on':'');
  document.getElementById('btn-riichi').textContent=r?'已宣告立直':'未宣告';
  checkAndShowResult();
}}

let drawnTile = null;   // 最後摸入的牌（不參與排序）

// 手牌排序：1m~9m, 1p~9p, 1s~9s, 東南西北白發中
const SUIT_SORT  = {{'m':0,'p':1,'s':2}};
const HONOR_SORT = {{'東':0,'南':1,'西':2,'北':3,'白':4,'發':5,'中':6}};

function tileRank(name) {{
  if (HONOR_SORT.hasOwnProperty(name)) return [3, HONOR_SORT[name], 0];
  const isRed=name.includes('r'), clean=name.replace('r','');
  return [SUIT_SORT[clean[clean.length-1]], parseInt(clean[0]), isRed?1:0];
}}
function sortHand() {{
  hand.sort((a,b) => {{
    const ra=tileRank(a.name), rb=tileRank(b.name);
    for (let i=0;i<ra.length;i++) if (ra[i]!==rb[i]) return ra[i]-rb[i];
    return 0;
  }});
}}

// ── 模式切換（Tab 鍵 / 按鈕）──
function setMode(m) {{
  mode = m;
  document.getElementById('btn-hand').className  = 'mode-btn' + (m==='hand'  ? ' hand-on'  : '');
  document.getElementById('btn-fuuro').className = 'mode-btn' + (m==='fuuro' ? ' fuuro-on' : '');
  document.getElementById('btn-dora').className  = 'mode-btn' + (m==='dora'  ? ' dora-on'  : '');
  document.getElementById('hand-area').classList.toggle('area-on',  m==='hand');
  document.getElementById('fuuro-area').classList.toggle('area-on', m==='fuuro');
  document.getElementById('dora-area').classList.toggle('area-on',  m==='dora');
  hideWarning();
}}
document.addEventListener('keydown', e => {{
  if (e.key === 'Tab') {{
    e.preventDefault();
    const order=['hand','fuuro','dora'];
    setMode(order[(order.indexOf(mode)+1)%3]);
  }}
}});

// ── 建立牌庫 ──
const pickerEl = document.getElementById('picker');
rows.forEach(row => {{
  const rowDiv = document.createElement('div');
  rowDiv.className = 'tile-row';
  row.forEach(t => {{
    const div=document.createElement('div'); div.className='tile'; div.title=t.name;
    div.onclick=()=>addTile(t.name,t.src);
    const im=document.createElement('img'); im.src=t.src; im.alt=t.name;
    div.appendChild(im); rowDiv.appendChild(div);
  }});
  pickerEl.appendChild(rowDiv);
}});

// ── 牌名 → 圖片路徑對應表（供文字輸入解析） ──
const tileMap = {{}};
rows.forEach(row => row.forEach(t => {{ tileMap[t.name] = t.src; }}));

function setPickerDisabled(d) {{
  document.querySelectorAll('.tile').forEach(el=>el.classList.toggle('full',d));
}}

// ── 警語 ──
function showWarning(msg) {{
  const el=document.getElementById('warn-msg');
  el.textContent='⚠ '+msg; el.style.display='block';
}}
function hideWarning() {{ document.getElementById('warn-msg').style.display='none'; }}

function totalTiles() {{ return hand.length + fuuro.length + (drawnTile?1:0); }}

// ── 寶牌指示牌 ──
let doraIndicators = [];

function doraFromIndicator(indNorm) {{
  const WIND_CYCLE   = ['東','南','西','北'];
  const DRAGON_CYCLE = ['白','發','中'];
  const wi = WIND_CYCLE.indexOf(indNorm);
  if (wi >= 0) return WIND_CYCLE[(wi+1)%4];
  const di = DRAGON_CYCLE.indexOf(indNorm);
  if (di >= 0) return DRAGON_CYCLE[(di+1)%3];
  const n = tileNum(indNorm), s = tileSuit(indNorm);
  return `${{n===9?1:n+1}}${{s}}`;
}}

function removeDoraIndicator(idx) {{
  doraIndicators.splice(idx,1);
  document.getElementById('result-area').style.display='none';
  renderDora(); checkAndShowResult();
}}

function renderDora() {{
  const el=document.getElementById('dora-display');
  document.getElementById('dora-count').textContent=doraIndicators.length+' / 8';
  if (doraIndicators.length===0) {{
    el.innerHTML='<span class="hint">切換至寶牌模式後點擊牌庫加入指示牌</span>'; return;
  }}
  el.innerHTML='';
  doraIndicators.forEach((t,i) => {{
    const actualDora=doraFromIndicator(norm(t.name));
    const wrap=document.createElement('div'); wrap.className='dora-pair';
    const div=document.createElement('div'); div.className='placed-tile is-dora';
    div.title=`${{t.name}} → 寶牌：${{actualDora}} — 點擊移除`; div.onclick=()=>removeDoraIndicator(i);
    const im=document.createElement('img'); im.src=t.src; im.alt=t.name;
    div.appendChild(im);
    const lbl=document.createElement('div'); lbl.className='dora-arrow'; lbl.textContent='↓ '+actualDora;
    wrap.appendChild(div); wrap.appendChild(lbl); el.appendChild(wrap);
  }});
}}

// ── 加牌（驗證橫跨手牌＋副露＋寶牌指示牌）──
function addTile(name, src) {{
  const normName=norm(name), isRed=name.includes('r');
  const combined=[...hand,...(drawnTile?[drawnTile]:[]),...fuuro,...doraIndicators];
  const normCount=combined.filter(t=>norm(t.name)===normName).length;
  const redCount =combined.filter(t=>t.name===name).length;

  // 寶牌模式：獨立加入指示牌
  if (mode==='dora') {{
    if (doraIndicators.length>=8) {{ showWarning('寶牌指示牌最多 8 張'); return; }}
    if (normCount>=4) {{ showWarning(`${{normName}} 已有 4 張（含手牌、副露），無法再加入`); return; }}
    if (isRed && redCount>=1) {{ showWarning(`${{name}} 為紅五，每種紅五最多只能有 1 張`); return; }}
    hideWarning();
    doraIndicators.push({{name,src}}); renderDora(); checkAndShowResult(); return;
  }}

  if (totalTiles()>=14) return;

  if (normCount>=4) {{
    showWarning(`${{normName}} 已有 4 張（含副露、寶牌指示牌），無法再加入`);
    return;
  }}
  if (isRed && redCount>=1) {{
    showWarning(`${{name}} 為紅五，每種紅五最多只能有 1 張`);
    return;
  }}

  hideWarning();
  if (mode==='hand') {{
    if (hand.length < 13 - fuuro.length) {{
      hand.push({{name,src}}); sortHand();   // 前 maxH-1 張排序
    }} else {{
      drawnTile={{name,src}};               // 最後一張獨立區域
    }}
    if (totalTiles()>=14) setPickerDisabled(true);
    renderHand();
    checkAndShowResult();
  }} else {{
    if (totalTiles()===13) {{
      showWarning('最後一張牌必須加入手牌，請切換至手牌模式');
      return;
    }}
    fuuro.push({{name,src}});
    renderFuuro();
    checkAndShowResult();
    if (totalTiles()===13) setMode('hand');
  }}
}}

// ── 移除 ──
function removeTile(idx) {{
  hand.splice(idx,1); setPickerDisabled(false); hideWarning();
  document.getElementById('result-area').style.display='none';
  renderHand();
}}
function removeDrawnTile() {{
  drawnTile=null; setPickerDisabled(false); hideWarning();
  renderHand(); checkAndShowResult();
}}
function removeFuuroTile(idx) {{
  fuuro.splice(idx,1); setPickerDisabled(false); hideWarning();
  document.getElementById('result-area').style.display='none';
  renderFuuro();
}}

// ── 清空 ──
function clearArea(area) {{
  if (area==='hand') {{
    hand=[]; drawnTile=null; setPickerDisabled(false); hideWarning();
    document.getElementById('result-area').style.display='none';
    renderHand();
  }} else if (area==='fuuro') {{
    fuuro=[]; setPickerDisabled(false); hideWarning();
    document.getElementById('result-area').style.display='none';
    renderFuuro();
  }} else {{
    doraIndicators=[];
    document.getElementById('result-area').style.display='none';
    renderDora();
  }}
}}

// ── 渲染手牌 ──
function renderHand() {{
  const el=document.getElementById('hand');
  const maxH=14-fuuro.length;
  const total=hand.length+(drawnTile?1:0);
  document.getElementById('count').textContent=total+' / '+maxH;
  document.getElementById('full-warn').style.display=total>=maxH?'block':'none';
  if (hand.length===0 && !drawnTile) {{
    el.innerHTML='<span class="hint">點擊牌庫加入手牌；點擊手牌移除</span>'; return;
  }}
  el.innerHTML='';
  hand.forEach((t,i) => {{
    const div=document.createElement('div'); div.className='placed-tile is-hand';
    div.title=`${{t.name}} — 點擊移除`; div.onclick=()=>removeTile(i);
    const im=document.createElement('img'); im.src=t.src; im.alt=t.name;
    div.appendChild(im); el.appendChild(div);
  }});
  if (drawnTile) {{
    const sep=document.createElement('div'); sep.className='hand-sep'; el.appendChild(sep);
    const wrap=document.createElement('div'); wrap.className='last-tile-wrap';
    const lbl=document.createElement('div'); lbl.className='last-tile-label'; lbl.textContent='摸牌';
    const div=document.createElement('div'); div.className='placed-tile is-hand';
    div.title=`${{drawnTile.name}} — 點擊移除`; div.onclick=()=>removeDrawnTile();
    const im=document.createElement('img'); im.src=drawnTile.src; im.alt=drawnTile.name;
    div.appendChild(im); wrap.appendChild(lbl); wrap.appendChild(div); el.appendChild(wrap);
  }}
}}

// ── 渲染副露 ──
function renderFuuro() {{
  const el=document.getElementById('fuuro');
  const fWarn=fuuro.length>0&&fuuro.length%3!==0?' ⚠ 需為 3 的倍數':'';
  document.getElementById('fuuro-count').textContent=fuuro.length+' 張'+fWarn;
  if (fuuro.length===0) {{ el.innerHTML='<span class="hint">切換至副露模式後點擊牌庫加入</span>'; return; }}
  el.innerHTML='';
  fuuro.forEach((t,i) => {{
    const div=document.createElement('div'); div.className='placed-tile is-fuuro';
    div.title=`${{t.name}} — 點擊移除`; div.onclick=()=>removeFuuroTile(i);
    const im=document.createElement('img'); im.src=t.src; im.alt=t.name;
    div.appendChild(im); el.appendChild(div);
  }});
}}

// ── 符數計算 ──
function calcFu(yaku, handNames, fuuroNames, winNorm, isTsumo) {{
  if (yaku.some(y=>y.includes('七對子'))) return 25;
  const isPinfu=yaku.some(y=>y.includes('平和'));
  if (isPinfu) return isTsumo ? 20 : 30;
  let fu=20;
  if (fuuroNames.length===0 && !isTsumo) fu+=10; // 門清榮和
  if (isTsumo) fu+=2;
  const allNorm=[...handNames,...fuuroNames].map(n=>norm(n));
  const counts=handToCounts(allNorm);
  const decomp=getDecomposition(counts);
  if (!decomp) return Math.ceil(fu/10)*10;
  const {{sequences,triplets,pair}}=decomp;
  const fc=handToCounts(fuuroNames.map(n=>norm(n)));
  for (const t of triplets) {{
    const isOpen=(fc[t]||0)>=3 || (!isTsumo && t===winNorm && pair!==winNorm);
    const isBig=isHonor(t)||tileNum(t)===1||tileNum(t)===9;
    fu+=isOpen?(isBig?4:2):(isBig?8:4);
  }}
  // 雀頭符
  if (['中','白','發'].includes(pair)) fu+=2;
  if (pair===roundWind) fu+=2;
  if (pair===seatWind) fu+=2;
  // 待牌符
  if (pair===winNorm) {{
    fu+=2; // 單騎待
  }} else if (triplets.includes(winNorm)) {{
    // 雙碰 0 符
  }} else {{
    for (const seq of sequences) {{
      if (!seq.includes(winNorm)) continue;
      const wn=tileNum(winNorm);
      const nums=seq.map(t=>tileNum(t)).sort((a,b)=>a-b);
      if (wn===nums[1]) {{ fu+=2; break; }} // 嵌張
      if ((wn===nums[0]&&nums[2]===9)||(wn===nums[2]&&nums[0]===1)) {{ fu+=2; break; }} // 辺張
      break; // 兩面 0 符
    }}
  }}
  return Math.ceil(fu/10)*10;
}}

// ── 點數計算 ──
function getScoreStr(han, fu, isTsumo, isDealer) {{
  const basic=fu*Math.pow(2,han+2);
  const round=v=>Math.ceil(v/100)*100;
  // 滿貫以上固定點數
  if (han>=13) return isTsumo?(isDealer?'各16000（自摸）':'莊16000閒各8000（自摸）'):(isDealer?48000:32000)+'點（榮和）';
  if (han>=11) return isTsumo?(isDealer?'各12000（自摸）':'莊12000閒各6000（自摸）'):(isDealer?36000:24000)+'點（榮和）';
  if (han>=8)  return isTsumo?(isDealer?'各8000（自摸）':'莊8000閒各4000（自摸）'):(isDealer?24000:16000)+'點（榮和）';
  if (han>=6)  return isTsumo?(isDealer?'各6000（自摸）':'莊6000閒各3000（自摸）'):(isDealer?18000:12000)+'點（榮和）';
  if (han>=5||basic>=2000) return isTsumo?(isDealer?'各4000（自摸）':'莊4000閒各2000（自摸）'):(isDealer?12000:8000)+'點（榮和）';
  if (isTsumo) {{
    const oya=round(basic*2), ko=round(basic);
    return isDealer?`各${{oya}}點（自摸）`:`莊${{oya}}閒各${{ko}}點（自摸）`;
  }}
  return round(basic*(isDealer?6:4))+'點（榮和）';
}}

// ── 文字輸入解析 ──
function showInputWarn(msg) {{
  const el=document.getElementById('input-warn');
  el.textContent='⚠ '+msg; el.style.display='block';
}}
function hideInputWarn() {{ document.getElementById('input-warn').style.display='none'; }}

function parseTileInput() {{
  const raw=document.getElementById('tile-input').value;
  const HONOR_CHARS='東南西北白發中';
  const names=[];
  let digits='';
  for (let i=0;i<raw.length;i++) {{
    const ch=raw[i];
    if ('0123456789'.includes(ch)) {{
      digits+=ch;
    }} else if ('mMpPsS'.includes(ch)) {{
      const s=ch.toLowerCase();
      for (const d of digits) names.push(d==='0'?`5r${{s}}`:`${{d}}${{s}}`);
      digits='';
    }} else if (HONOR_CHARS.includes(ch)) {{
      digits=''; names.push(ch);
    }} else {{
      digits=''; // 空格或未知字元，重置數字緩衝
    }}
  }}
  if (!names.length) {{
    showInputWarn('無法解析。格式範例：123m456p789s東東白，0m/0p/0s 代表紅五');
    return;
  }}
  hideInputWarn();
  let unknown=0;
  for (const name of names) {{
    const src=tileMap[name];
    if (!src) {{ unknown++; continue; }}
    addTile(name, src);
  }}
  if (unknown>0) showInputWarn(`${{unknown}} 張牌名稱無法識別，其餘已加入`);
  else {{ hideInputWarn(); document.getElementById('tile-input').value=''; }}
}}

// ── 聽牌計算 ──
const ALL_TILES_NORM=[
  '1m','2m','3m','4m','5m','6m','7m','8m','9m',
  '1p','2p','3p','4p','5p','6p','7p','8p','9p',
  '1s','2s','3s','4s','5s','6s','7s','8s','9s',
  '東','南','西','北','白','發','中'
];

function showTenpai() {{
  const area=document.getElementById('result-area');
  area.style.display='block';
  const handN=hand.map(t=>t.name);
  const fuuroN=fuuro.map(t=>t.name);
  const waits=[];
  for (const tile of ALL_TILES_NORM) {{
    const testN=[...handN,tile];
    const yakuBase=fuuroN.length===0?checkYaku(testN,tile):checkYakuOpen(testN,fuuroN,tile);
    const hv=(()=>{{const c=handToCounts(testN);return isKokushi(c)||isChiitoitsu(c)||getDecomposition(c)!==null;}})();
    const yaku=(isRiichi&&fuuroN.length===0&&hv)?['立直 (1翻)',...yakuBase]:yakuBase;
    if (!yaku.length) continue;
    let han=0,isYk=false;
    for (const y of yaku) {{
      if (y.includes('役滿')) {{isYk=true;break;}}
      const m=y.match(/\((\d+)翻\)/); if(m) han+=parseInt(m[1]);
    }}
    // 手牌＋副露中的赤五與寶牌
    const allNrm=[...testN,...fuuroN].map(n=>norm(n));
    const redCnt=[...handN,...fuuroN].filter(n=>n.includes('r')).length;
    let doraH=0;
    for (const ind of doraIndicators) {{
      const ad=doraFromIndicator(norm(ind.name));
      doraH+=allNrm.filter(t=>t===ad).length;
    }}
    if (!isYk) {{ han+=redCnt; han+=doraH; }}
    let hanFuStr,scoreStr;
    if (isYk) {{
      hanFuStr='役滿';
      scoreStr=isTsumo?(isDealer?'各16000':'莊16000/各8000'):(isDealer?'48000':'32000')+'點';
    }} else {{
      const fu=calcFu(yaku,testN,fuuroN,tile,isTsumo);
      scoreStr=getScoreStr(han,fu,isTsumo,isDealer);
      const basic=fu*Math.pow(2,han+2);
      const tier=han>=13?'役滿':han>=11?'三倍滿':han>=8?'倍滿':han>=6?'跳滿':(han>=5||basic>=2000)?'滿貫':'';
      hanFuStr=tier?(tier==='滿貫'&&han<5?`${{han}}翻${{fu}}符【滿貫】`:`${{han}}翻【${{tier}}】`):`${{han}}翻${{fu}}符`;
    }}
    waits.push({{tile,hanFuStr,scoreStr}});
  }}
  if (!waits.length) {{
    area.className='result-area result-lose';
    area.innerHTML='<strong>⛔ 非聽牌</strong>';
    return;
  }}
  const modeTxt=isTsumo?'自摸':'榮和';
  const riichiTxt=isRiichi?'立直・':'';
  let html=`<strong>🎯 聽牌（${{riichiTxt}}${{isDealer?'親家':'子家'}}・${{modeTxt}}）</strong><div class="wait-grid">`;
  for (const w of waits) {{
    const src=tileMap[w.tile]||'';
    html+=`<div class="wait-item"><div class="placed-tile is-hand" style="cursor:default;pointer-events:none"><img src="${{src}}" alt="${{w.tile}}"></div><div class="wait-han-fu">${{w.hanFuStr}}</div><div class="wait-pts">${{w.scoreStr}}</div></div>`;
  }}
  html+='</div><div class="note">※ 和牌張本身若為赤五，另計 +1 翻</div>';
  area.className='result-area result-tenpai';
  area.innerHTML=html;
  area.scrollIntoView({{behavior:'smooth',block:'nearest'}});
}}

// ── 和牌判定 ──
function checkAndShowResult() {{
  const area=document.getElementById('result-area');
  const total=totalTiles();
  if (total<13) {{ area.style.display='none'; return; }}
  if (fuuro.length>0 && fuuro.length%3!==0) {{
    area.style.display='block';
    area.className='result-area result-lose';
    area.innerHTML='<strong>⚠ 副露牌數需為 3 的倍數（現為 '+fuuro.length+' 張）</strong>';
    return;
  }}
  if (total===13) {{ showTenpai(); return; }}
  showResult();
}}

function showResult() {{
  const area=document.getElementById('result-area');
  area.style.display='block';
  const handN=[...hand.map(t=>t.name), ...(drawnTile?[drawnTile.name]:[])];
  const fuuroN=fuuro.map(t=>t.name);
  const winNorm=norm(drawnTile.name);
  const yakuBase=fuuro.length===0 ? checkYaku(handN, winNorm) : checkYakuOpen(handN, fuuroN, winNorm);
  // 立直：牌型必須能組成有效和牌形式才能以立直成役（避免無效牌型偽裝成和牌）
  const handIsValid=(()=>{{const c=handToCounts(handN);return isKokushi(c)||isChiitoitsu(c)||getDecomposition(c)!==null;}})();
  const yaku=(isRiichi&&fuuro.length===0&&handIsValid)?['立直 (1翻)',...yakuBase]:yakuBase;
  if (yaku.length===0) {{
    area.className='result-area result-lose';
    area.innerHTML='<strong>❌ 無役（不能和牌）</strong>';
    return;
  }}
  // 翻數計算
  let han=0; let isYakuman=false;
  for (const y of yaku) {{
    if (y.includes('役滿')) {{ isYakuman=true; break; }}
    const m=y.match(/\((\d+)翻\)/);
    if (m) han+=parseInt(m[1]);
  }}
  // 紅五各 +1 翻
  const allTileNames=[...handN,...fuuroN];
  const redCount=allTileNames.filter(n=>n.includes('r')).length;
  han+=redCount;
  const redChips=Array.from({{length:redCount}},()=>'<span class="yaku-item">赤ドラ (1翻)</span>').join('');
  // 寶牌各 +1 翻
  const allNorm=allTileNames.map(n=>norm(n));
  let doraHan=0; let doraChips='';
  for (const ind of doraIndicators) {{
    const actualDora=doraFromIndicator(norm(ind.name));
    const cnt=allNorm.filter(t=>t===actualDora).length;
    doraHan+=cnt;
    doraChips+=Array.from({{length:cnt}},()=>`<span class="yaku-item">寶牌：${{actualDora}} (1翻)</span>`).join('');
  }}
  if (!isYakuman) han+=doraHan;
  const chips=yaku.map(y=>`<span class="yaku-item">${{y}}</span>`).join('')+redChips+doraChips;
  // 符數與點數
  let scoreHTML='';
  if (isYakuman) {{
    const scoreStr=isTsumo
      ?(isDealer?'各16000（自摸）':'莊16000閒各8000（自摸）')
      :(isDealer?'48000點（榮和）':'32000點（榮和）');
    scoreHTML='<div class="score-line">役滿 ✦</div><div class="han-fu">'+scoreStr+'</div>';
  }} else {{
    const fu=calcFu(yaku, handN, fuuroN, winNorm, isTsumo);
    const scoreStr=getScoreStr(han, fu, isTsumo, isDealer);
    const basic=fu*Math.pow(2,han+2);
    const tier=han>=13?'役滿':han>=11?'三倍滿':han>=8?'倍滿':han>=6?'跳滿':(han>=5||basic>=2000)?'滿貫':'';
    const hanFuStr=tier
      ?(tier==='滿貫'&&han<5?`${{han}}翻 ${{fu}}符【滿貫】`:`${{han}}翻【${{tier}}】`)
      :`${{han}}翻 ${{fu}}符`;
    scoreHTML='<div class="score-line">'+hanFuStr+'</div><div class="han-fu">'+scoreStr+'</div>';
  }}
  const note=fuuro.length===0
    ? (isRiichi?'※ 已排除搶槓、嶺上、海底等場況役。一發需自行確認。':'※ 已排除搶槓、嶺上、海底等場況役。立直需自行確認是否已宣告。')
    : '※ 副露手牌，已排除門清限定役（立直、一發、門清自摸、一盃口、二盃口、九蓮寶燈等）。';
  area.className='result-area result-win';
  area.innerHTML='<strong>✅ 可以和牌！</strong>'
    +'<div class="yaku-chips">'+chips+'</div>'
    +scoreHTML
    +'<div class="note">'+note+'</div>';
  area.scrollIntoView({{behavior:'smooth',block:'nearest'}});
}}

renderHand();
renderFuuro();
renderDora();
document.getElementById('tile-input').addEventListener('keydown', e=>{{
  if (e.key==='Enter') {{ e.preventDefault(); parseTileInput(); }}
}});
</script>
</body>
</html>
"""

st.title("麻將手牌選擇器")
components.html(html, height=950, scrolling=True)
