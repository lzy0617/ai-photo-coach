export function normalizedBox(person, image) {
  let box = person.bbox_norm
  if (!box && image?.width > 0 && image?.height > 0 && person.bbox) {
    const b = person.bbox
    box = { x1: b.x1 / image.width, y1: b.y1 / image.height, x2: b.x2 / image.width, y2: b.y2 / image.height }
  }
  if (!box || !['x1', 'y1', 'x2', 'y2'].every(key => Number.isFinite(box[key]))) return null
  const clamped = Object.fromEntries(Object.entries(box).map(([key, value]) => [key, Math.max(0, Math.min(1, value))]))
  return clamped.x2 > clamped.x1 && clamped.y2 > clamped.y1 ? clamped : null
}

/**
 * 标签不应受人物框宽度限制。人物位于画面右半区时，让标签从框的
 * 右边缘向左展开；其余情况从左边缘向右展开，减少被画面裁切的概率。
 */
export function boxLabelAlignment(box) {
  if (!box || !Number.isFinite(box.x1) || !Number.isFinite(box.x2)) return 'left'
  return (box.x1 + box.x2) / 2 > 0.5 ? 'right' : 'left'
}
