const API_BASE = "/api/dashboard";

async function request(url, options = {}) {
    const response = await fetch(url, {
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {})
        },
        ...options
    });

    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }

    return response.json();
}

export const DashboardAPI = {
    getDashboard(userId) {
        return request(`${API_BASE}/${userId}`);
    }
};
