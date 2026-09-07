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
