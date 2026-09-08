// 仅转换展示文案，不改变 Edge 返回的数据或评分规则。
export const NO_PERSON_MESSAGE = '暂未检测到清晰人物，请调整取景后再试。'
export const MULTI_PERSON_MESSAGE = '检测到多位人物。当前构图规则主要针对单人人像，以下结果仅作为位置参考。'
export const REFERENCE_DESCRIPTION = '基于人物位置、画面占比与留白关系进行几何参考，不代表完整审美评价。'

export function friendlyText(value) {
  if (typeof value !== 'string') return ''
  const text = value.replaceAll('头顶', '上方').replaceAll('顶部', '上方')
  const mappings = [
    [/人物向左移动/, '可以尝试让人物稍向左移动。'],
    [/人物向右移动/, '可以尝试让人物稍向右移动。'],
    [/减少人物上方空白|缩小上方留白/, '可以尝试减少一些上方留白。'],
    [/扩大上方取景|增加上方空间/, '可以尝试增加一些人物上方空间。'],
    [/建议靠近人物或使用更长焦距|可以适当靠近人物/, '如果希望突出人物，可以尝试靠近一些。'],
    [/建议稍微远离人物/, '如果希望保留更多环境，可以尝试稍微远离人物。'],
    [/如果希望保留环境/, '如果希望保留环境，可以适当扩大取景范围。'],
    [/当前基础构图较稳定/, '当前构图关系较稳定，可以继续关注背景与光线。'],
    [/主体横向位置基本合适/, '当前主体位置较稳定。'],
    [/主体与三分线有一定距离/, '主体与三分线有一定距离，可以根据拍摄意图选择位置。'],
    [/主体横向位置较难形成/, '主体偏离三分线，可以根据拍摄意图选择位置。'],
    [/视觉重点不够突出/, '人物在画面中占比较小，可以根据表达需要保留环境。'],
  ]
  return mappings.find(([pattern]) => pattern.test(text))?.[1] ?? text
}

export function dimensionPresentation(key, data) {
  const comment = friendlyText(data?.comment)
  if (!data) return { state: '等待分析', comment: '选择照片后查看构图关系。' }
  let state = '位置参考'
  if (key === 'position') {
    if (data.style === 'centered' || /接近画面中心/.test(comment)) state = '居中稳定'
    else if (/非常接近三分线|较接近三分线/.test(comment)) state = '接近三分线'
    else if (/三分线/.test(comment)) state = '偏离三分线'
  } else if (key === 'headroom') {
    state = /稍多/.test(comment) ? '稍多' : /较多/.test(comment) ? '偏多' : /略紧/.test(comment) ? '略紧' : /贴近/.test(comment) ? '较少' : /自然/.test(comment) ? '适中' : '留白参考'
  } else if (key === 'subject_size') {
    state = /略小/.test(comment) ? '略小' : /偏小|占比较小/.test(comment) ? '偏小' : /过大/.test(comment) ? '偏大' : /较大/.test(comment) ? '较大' : /合适/.test(comment) ? '合适' : '占比参考'
  }
  return { state, comment: comment || '可结合拍摄意图查看这一关系。' }
}

export function brightnessPresentation(data) {
  if (!data) return { state: '等待分析', comment: '选择照片后查看亮度分布。', notes: [] }
  if (data.status === 'error') return { state: '暂不可用', comment: '暂时无法读取亮度统计，可以稍后重试。', notes: [] }
  const descriptions = {
    dark: ['偏暗', '画面整体偏暗；如果并非刻意营造低调氛围，可以尝试适当增加曝光。'],
    slightly_dark: ['略暗', '画面略偏暗，可根据拍摄意图决定是否增加曝光。'],
    normal: ['自然', '整体亮度分布较自然。'],
    slightly_bright: ['略亮', '画面略偏亮，可根据拍摄意图决定是否调整曝光。'],
    bright: ['偏亮', '画面整体偏亮；如果并非刻意的高调效果，可以注意高光区域。'],
  }
  const [state, comment] = descriptions[data.tendency] ?? ['亮度参考', friendlyText(data.comment) || '暂无亮度描述。']
  const notes = []
  if (data.dark_ratio > 0.30) notes.push('暗部占比较高')
  if (data.highlight_ratio > 0.12) notes.push('高光区域占比较高')
  return { state, comment, notes }
}

export function guideStatus(result, noPerson, multiplePersons) {
  if (!result) return '等待取景'
  if (noPerson) return '等待清晰人物'
  if (multiplePersons) return '多人位置参考'
  // 沿用后端的稳定结论文案，不通过新的分数阈值推断审美质量。
  const suggestions = result.composition?.suggestions
  if (Array.isArray(suggestions) && suggestions.some(text => typeof text === 'string' && /构图较稳定|构图关系较稳定/.test(text))) return '关系较稳定'
  return '可尝试调整'
}

// 按现有建议的类别排序，不增加新的图像评分规则。
export function liveAdvice(result) {
  if (!result) return '让人物进入画面，等待一次构图分析。'
  if (result.composition?.status === 'no_person' || !result.detection?.persons?.length) return NO_PERSON_MESSAGE
  const raw = result.composition?.suggestions ?? result.suggestions
  const items = Array.isArray(raw) ? raw.filter(text => typeof text === 'string') : []
  const priority = text => /向左|向右|边缘|横向位置/.test(text) ? 0
    : /留白|上方|顶部|头顶/.test(text) ? 1
      : /靠近|远离|占比|主体.*[大小]|取景范围|长焦/.test(text) ? 2 : 3
  const selected = items.map((text, index) => ({ text, index, rank: priority(text) }))
    .sort((a, b) => a.rank - b.rank || a.index - b.index)[0]?.text
  if (!selected || /构图较稳定|构图关系较稳定/.test(selected)) return '✓ 当前构图比较稳定'
  const text = friendlyText(selected)
  if (/向左/.test(text)) return '← 可以稍向左调整'
  if (/向右/.test(text)) return '→ 可以稍向右调整'
  if (/减少.*上方留白/.test(text)) return '↑ 可以减少一些上方留白'
  if (/增加.*上方空间/.test(text)) return '可以增加一些人物上方空间'
  return text
}
