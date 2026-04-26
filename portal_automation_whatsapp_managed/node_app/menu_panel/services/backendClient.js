const axios = require("axios");

class PanelBackendClient {
  constructor({ baseURL, timeoutMs }) {
    this.api = axios.create({
      baseURL,
      timeout: timeoutMs,
      headers: {
        "Content-Type": "application/json",
      },
    });
  }

  normalizeError(error) {
    const detail = error.response?.data?.detail || error.message || "Unknown backend error.";
    const normalizedError = new Error(detail);
    normalizedError.statusCode = error.response?.status || 500;
    return normalizedError;
  }

  async get(path) {
    try {
      const response = await this.api.get(path);
      return response.data;
    } catch (error) {
      throw this.normalizeError(error);
    }
  }

  async post(path, payload = {}) {
    try {
      const response = await this.api.post(path, payload);
      return response.data;
    } catch (error) {
      throw this.normalizeError(error);
    }
  }

  login() {
    return this.post("/panel/auth/login");
  }

  refreshSession() {
    return this.post("/panel/session/refresh");
  }

  logout() {
    return this.post("/panel/session/logout");
  }

  startManualAttendance() {
    return this.get("/panel/attendance/manual");
  }

  markAttendance(student, status) {
    return this.post("/panel/attendance/mark", { student, status });
  }

  markAllPresent() {
    return this.post("/panel/attendance/all-present");
  }

  fetchStudents() {
    return this.post("/panel/students/fetch");
  }

  searchStudents(query) {
    return this.post("/panel/assignment/search", { query });
  }

  generateAssignment(student, topic) {
    return this.post("/panel/assignment/generate", { student, topic });
  }

  deployAssignment(student, assignment) {
    return this.post("/panel/assignment/deploy", { student, assignment });
  }

  status(whatsappAuthenticated) {
    return this.post("/panel/status", { whatsapp_authenticated: whatsappAuthenticated });
  }
}

module.exports = {
  PanelBackendClient,
};
