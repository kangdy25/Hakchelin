export default defineNuxtRouteMiddleware(async (_to, _from) => {
  const { profile, refreshProfile, isAdmin } = useUserProfile()

  // 만약 프로필이 로드되지 않았거나 비어 있다면 새로고침
  if (!profile.value || !profile.value.student_id) {
    await refreshProfile()
  }

  // 관리자가 아니라면 메인 페이지로 리다이렉트
  if (!isAdmin.value) {
    if (process.client) {
      alert('관리자 권한이 필요합니다. (Admin access required)')
    }
    return navigateTo('/')
  }
})
