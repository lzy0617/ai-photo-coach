// 必须在用户点击事件中调用；参数始终为原始 File，而非分析副本。
export async function savePhoto(file) {
  if (!file) throw new Error('请先拍摄或选择照片。')
  const url = URL.createObjectURL(file)
  const anchor = document.createElement('a')
  try {
    anchor.href = url
    anchor.download = file.name || 'photo.jpg'
    document.body.appendChild(anchor)
    anchor.click()
    return '已发起原图下载，请查看浏览器下载记录。'
  } finally {
    anchor.remove()
    // 留出浏览器开始读取下载资源的时间，避免立即释放导致移动端下载失败。
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }
}
