const MAX_EDGE = 640
const JPEG_QUALITY = 0.80

/** 快速分析专用副本；不修改原始 File，不裁剪、不补边、不放大。 */
export async function prepareFastImage(file) {
  const started = performance.now()
  const url = URL.createObjectURL(file)
  const image = new Image()
  let canvas
  try {
    image.src = url
    try {
      // 使用与原图预览一致的浏览器解码方向（包括 EXIF 方向）。
      await image.decode()
    } catch {
      throw new Error('浏览器无法读取这张照片，请改用 JPG、PNG 或 WebP 格式。')
    }
    const originalWidth = image.naturalWidth
    const originalHeight = image.naturalHeight
    if (!originalWidth || !originalHeight) throw new Error('图片尺寸无效，请选择其他照片。')
    const scale = Math.min(1, MAX_EDGE / Math.max(originalWidth, originalHeight))
    canvas = document.createElement('canvas')
    // Canvas 尺寸必须为整数，短边最多产生半像素的舍入误差。
    canvas.width = Math.max(1, Math.round(originalWidth * scale))
    canvas.height = Math.max(1, Math.round(originalHeight * scale))
    const context = canvas.getContext('2d')
    if (!context) throw new Error('浏览器无法处理图片，请重试或更换浏览器。')
    // JPEG 不支持透明通道，与页面的浅色预览背景保持一致。
    context.fillStyle = '#ffffff'
    context.fillRect(0, 0, canvas.width, canvas.height)
    context.drawImage(image, 0, 0, canvas.width, canvas.height)
    const blob = await new Promise((resolve, reject) => {
      canvas.toBlob(value => value ? resolve(value) : reject(new Error('图片压缩失败，请重试。')), 'image/jpeg', JPEG_QUALITY)
    })
    if (blob.type !== 'image/jpeg') throw new Error('浏览器不支持 JPEG 压缩，请更换浏览器后重试。')
    const compressed = new File([blob], `${file.name.replace(/\.[^.]+$/, '') || 'photo'}-fast.jpg`, { type: 'image/jpeg' })
    if (import.meta.env?.DEV) {
      console.log('[AI Photo Coach] 快速分析图片预处理', {
        original: { width: originalWidth, height: originalHeight, bytes: file.size },
        compressed: { width: canvas.width, height: canvas.height, bytes: compressed.size },
        durationMs: Number((performance.now() - started).toFixed(1)),
      })
    }
    return compressed
  } finally {
    URL.revokeObjectURL(url)
    if (canvas) { canvas.width = 0; canvas.height = 0 }
  }
}
