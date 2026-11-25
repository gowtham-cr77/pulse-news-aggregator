const API_BASE = '/api';

const TOKEN_KEY = 'pulse_auth_token';

export function getStoredToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

async function request(path, options = {}) {
  const token = getStoredToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const errData = await res.json();
      if (typeof errData.detail === 'string') {
        message = errData.detail;
      } else if (Array.isArray(errData.detail) && errData.detail[0]?.msg) {
        message = errData.detail[0].msg;
      }
    } catch {
      // Ignore JSON parse failure
    }
    const err = new Error(message);
    err.status = res.status;
    throw err;
  }

  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  // Discovery
  getArticles(params = {}) {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '' && v !== 'all') {
        qs.set(k, String(v));
      }
    });
    return request(`/articles?${qs.toString()}`);
  },
  refreshLiveNews(region = 'all') {
    const qs = region && region !== 'all' ? `?region=${encodeURIComponent(region)}` : '';
    return request(`/articles/refresh${qs}`, { method: 'POST' });
  },
  getArticle(id) {
    return request(`/articles/${id}`);
  },
  getCategories(region = 'all') {
    const qs = region && region !== 'all' ? `?region=${encodeURIComponent(region)}` : '';
    return request(`/categories${qs}`);
  },
  getSources(region = 'all') {
    const qs = region && region !== 'all' ? `?region=${encodeURIComponent(region)}` : '';
    return request(`/sources${qs}`);
  },
  getTrending(window = '7d', limit = 10, region = 'all') {
    const qs = new URLSearchParams({ window, limit: String(limit) });
    if (region && region !== 'all') qs.set('region', region);
    return request(`/trending?${qs.toString()}`);
  },

  // Auth
  register(payload) {
    return request('/auth/register', { method: 'POST', body: JSON.stringify(payload) });
  },
  login(payload) {
    return request('/auth/login', { method: 'POST', body: JSON.stringify(payload) });
  },
  logout() {
    return request('/auth/logout', { method: 'POST' });
  },
  getMe() {
    return request('/auth/me');
  },

  // Personalization & Bookmarks
  getPreferences() {
    return request('/me/preferences');
  },
  updatePreferences(categoryIds) {
    return request('/me/preferences', {
      method: 'PUT',
      body: JSON.stringify({ category_ids: categoryIds }),
    });
  },
  getBookmarks(page = 1, size = 20) {
    return request(`/me/bookmarks?page=${page}&size=${size}`);
  },
  addBookmark(articleId) {
    return request(`/me/bookmarks/${articleId}`, { method: 'POST' });
  },
  removeBookmark(articleId) {
    return request(`/me/bookmarks/${articleId}`, { method: 'DELETE' });
  },

  // Admin
  getAdminFeeds() {
    return request('/admin/feeds');
  },
  createAdminFeed(payload) {
    return request('/admin/feeds', { method: 'POST', body: JSON.stringify(payload) });
  },
  updateAdminFeed(id, payload) {
    return request(`/admin/feeds/${id}`, { method: 'PATCH', body: JSON.stringify(payload) });
  },
  deleteAdminFeed(id) {
    return request(`/admin/feeds/${id}`, { method: 'DELETE' });
  },
  ingestAllFeeds() {
    return request('/admin/feeds/ingest', { method: 'POST' });
  },
  ingestSingleFeed(id) {
    return request(`/admin/feeds/${id}/ingest`, { method: 'POST' });
  },
  getIngestionRuns(limit = 50) {
    return request(`/admin/ingestion-runs?limit=${limit}`);
  },
  updateCategoryKeywords(categoryId, keywords) {
    return request(`/admin/categories/${categoryId}`, {
      method: 'PATCH',
      body: JSON.stringify({ keywords }),
    });
  },
  overrideArticleCategory(articleId, categoryId) {
    return request(`/admin/articles/${articleId}/category`, {
      method: 'PATCH',
      body: JSON.stringify({ category_id: categoryId }),
    });
  },
};
