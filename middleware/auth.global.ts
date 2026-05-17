export default defineNuxtRouteMiddleware((to, _from) => {
  const user = useSupabaseUser()
  
  // 1. /login 페이지로 갈 때
  if (to.path === '/login') {
    // 이미 로그인 상태라면 메인 페이지로 돌려보냄
    if (user.value) {
      return navigateTo('/')
    }
    return // 로그인 안 한 상태면 그대로 /login에 머물게 함
  }

  // 2. 다른 모든 페이지(예: /, /tickets, /history)로 갈 때
  // 로그인이 안 되어 있다면 강제로 /login 페이지로 보냄
  if (!user.value) {
    return navigateTo('/login')
  }
})
