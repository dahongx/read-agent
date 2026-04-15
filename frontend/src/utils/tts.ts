/**
 * Preprocess text before passing to speechSynthesis to improve TTS quality.
 *
 * Problems solved:
 * 1. Stage-direction markers like [停顿], [过渡], [强调] are stripped —
 *    they are cues for the speaker, not words to be read aloud.
 * 2. Math notation is converted to natural spoken Chinese:
 *    - M_{t+1}  →  "M t加1"
 *    - m_i      →  "m i"
 *    - g_write  →  "g write"
 *    - x^2      →  "x平方"
 *    - x^{n+1}  →  "x的n加1次方"
 */
export function preprocessForTts(text: string): string {
  // 1. Strip all bracket-enclosed markers: [停顿], [过渡], [1], etc.
  text = text.replace(/\[[^\]]*\]/g, '')

  // 2. LaTeX braced subscript: M_{t+1} → "M t加1"
  text = text.replace(/([A-Za-z\d])_\{([^}]+)\}/g, (_m, base, sub) =>
    base + ' ' + verbalizeMathExpr(sub)
  )

  // 3. LaTeX braced superscript: x^{n+1} → "x的n加1次方"
  text = text.replace(/([A-Za-z\d])\^\{([^}]+)\}/g, (_m, base, exp) =>
    base + '的' + verbalizeMathExpr(exp) + '次方'
  )

  // 4. Simple numeric superscript: x^2 → "x平方", x^3 → "x立方"
  text = text.replace(/([A-Za-z\d])\^(\d+)/g, (_m, base, exp) => {
    if (exp === '2') return base + '平方'
    if (exp === '3') return base + '立方'
    return base + '的' + exp + '次方'
  })

  // 5. Single-letter superscript: x^n → "x的n次方"
  text = text.replace(/([A-Za-z\d])\^([A-Za-z])/g, (_m, base, exp) =>
    base + '的' + exp + '次方'
  )

  // 6. Underscore subscript: m_i → "m i", g_write → "g write"
  //    Must run after braced variants (steps 2-3) so M_{t+1} isn't half-matched here.
  text = text.replace(/([A-Za-z\d])_([A-Za-z\d]+)/g, (_m, base, sub) =>
    base + ' ' + sub
  )

  // 7. Collapse extra whitespace left by removals
  text = text.replace(/\s{2,}/g, ' ').trim()

  return text
}

/** Convert arithmetic operators inside subscripts/superscripts to Chinese words. */
function verbalizeMathExpr(expr: string): string {
  return expr
    .replace(/\+/g, '加')
    .replace(/-/g, '减')
    .replace(/\*/g, '乘')
    .replace(/\//g, '除以')
}
