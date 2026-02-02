// src/utils/storage.ts
const getTokens = () => {
    const accessToken = localStorage.getItem("access_token");
    const refreshToken = localStorage.getItem("refresh_token");
    return { accessToken, refreshToken };
}

const saveTokens = (data: any) => {
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);
}

const clearTokens = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
}

export { getTokens, saveTokens, clearTokens };