export default defineNuxtRouteMiddleware(async (to, _from) => {
    const user = useSupabaseUser();
    const supabase = useSupabaseClient();
    const getUserId = (claims: unknown) => {
        const typedClaims = claims as { sub?: string; id?: string } | null;
        return typedClaims?.sub || typedClaims?.id || null;
    };
    let currentUser = user.value;

    if (!getUserId(currentUser)) {
        const { data } = await supabase.auth.getClaims();
        currentUser = data?.claims ?? null;

        if (currentUser) {
            user.value = currentUser;
        }
    }
    // 1. /login 페이지로 갈 때
    if (to.path === "/login") {
        // 이미 로그인 상태라면 메인 페이지로 돌려보냄
        if (getUserId(currentUser)) {
            return navigateTo("/");
        }
        return; // 로그인 안 한 상태면 그대로 /login에 머물게 함
    }

    // 2. 다른 모든 페이지(예: /, /tickets, /history)로 갈 때
    // 로그인이 안 되어 있다면 강제로 /login 페이지로 보냄
    if (!getUserId(currentUser)) {
        return navigateTo("/login");
    }
});
