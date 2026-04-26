const axios = require("axios");

class ConversationManager {
  constructor(apiBaseUrl) {
    this.api = axios.create({
      baseURL: apiBaseUrl,
      timeout: 60000,
      headers: {
        "Content-Type": "application/json",
      },
    });
    this.stateByChat = new Map();
  }

  async sendText(message, text) {
    await message.reply(text);
  }

  clear(chatId) {
    this.stateByChat.delete(chatId);
  }

  getStatusSummary(payload) {
    return [
      "*System Status*",
      `WhatsApp authenticated: ${payload.whatsapp_authenticated ? "yes" : "no"}`,
      `Backend reachable: ${payload.backend_reachable ? "yes" : "no"}`,
      `Session cookies: ${payload.session_cookies ? "yes" : "no"}`,
      `Trusted device token: ${payload.trusted_device ? "yes" : "no"}`,
      `CSRF token: ${payload.csrf_token ? "yes" : "no"}`,
      `Gemini API key: ${payload.gemini_api_key ? "yes" : "no"}`,
      `Student cache count: ${payload.student_cache_count}`,
      `Login ready: ${payload.login_ready ? "yes" : "no"}`,
    ].join("\n");
  }

  formatAssignmentPreview(student, topic, draft) {
    const questions = draft.questions.map((question, index) => `${index + 1}. ${question}`).join("\n");
    return [
      "*Assignment Preview*",
      `Student: ${student.name}`,
      `Course: ${student.course_name}`,
      `Topic: ${topic}`,
      "",
      `Title: ${draft.title}`,
      `Description: ${draft.description}`,
      "",
      "Questions:",
      questions,
      "",
      "Reply with: CONFIRM, REGENERATE, or CANCEL",
    ].join("\n");
  }

  async handleAttendanceEntry(message, chatId) {
    this.stateByChat.set(chatId, { flow: "attendance_mode" });
    await this.sendText(
      message,
      "Attendance mode selected.\nReply with:\n1. all present\n2. manual mode\n3. cancel"
    );
  }

  async handleAttendanceMode(message, chatId, text) {
    if (text === "cancel") {
      this.clear(chatId);
      await this.sendText(message, "Attendance workflow cancelled.");
      return;
    }

    if (text === "all present") {
      await this.sendText(message, "Marking all students present...");
      const { data } = await this.api.post("/attendance/all-present");
      this.clear(chatId);
      await this.sendText(
        message,
        `Attendance completed.\nTotal: ${data.total}\nSuccess: ${data.succeeded}\nFailed: ${data.failed}`
      );
      return;
    }

    if (text !== "manual mode") {
      await this.sendText(message, "Reply with `all present`, `manual mode`, or `cancel`.");
      return;
    }

    const { data } = await this.api.get("/attendance/snapshot");
    const nextState = {
      flow: "attendance_manual",
      students: data.students,
      csrfToken: data.csrf_token,
      index: 0,
      results: [],
    };
    this.stateByChat.set(chatId, nextState);
    await this.sendNextAttendanceStudent(message, chatId);
  }

  async sendNextAttendanceStudent(message, chatId) {
    const state = this.stateByChat.get(chatId);
    if (!state) {
      return;
    }

    if (state.index >= state.students.length) {
      const present = state.results.filter((item) => item === "Present").length;
      const absent = state.results.filter((item) => item === "Absent").length;
      const skipped = state.results.filter((item) => item === "Skip").length;
      this.clear(chatId);
      await this.sendText(
        message,
        `Manual attendance completed.\nPresent: ${present}\nAbsent: ${absent}\nSkipped: ${skipped}`
      );
      return;
    }

    const student = state.students[state.index];
    await this.sendText(
      message,
      `Student ${state.index + 1}/${state.students.length}\nName: ${student.name}\nID: ${student.student_id}\nBatch: ${student.batch}\nReply with: P, A, or S`
    );
  }

  async handleAttendanceManual(message, chatId, text) {
    const state = this.stateByChat.get(chatId);
    if (!state) {
      return;
    }

    const actionMap = {
      p: "Present",
      a: "Absent",
      s: "Skip",
    };
    const action = actionMap[text];
    if (!action) {
      await this.sendText(message, "Reply with `P`, `A`, or `S`.");
      return;
    }

    const student = state.students[state.index];
    if (action === "Skip") {
      state.results.push("Skip");
    } else {
      const { data } = await this.api.post("/attendance/mark", {
        student,
        status: action,
        csrf_token: state.csrfToken,
      });
      state.results.push(data.success ? action : "Skip");
      await this.sendText(
        message,
        data.success
          ? `${student.name} marked ${action}.`
          : `${student.name} failed with HTTP ${data.status_code}.`
      );
    }

    state.index += 1;
    this.stateByChat.set(chatId, state);
    await this.sendNextAttendanceStudent(message, chatId);
  }

  async handleAssignmentEntry(message, chatId) {
    this.stateByChat.set(chatId, { flow: "assignment_search" });
    await this.sendText(message, "Send a student name, student ID, or course keyword.");
  }

  async handleAssignmentSearch(message, chatId, text) {
    const { data } = await this.api.post("/assignment/search", { query: text });
    if (!data.matches.length) {
      await this.sendText(message, "No student match found. Try another search.");
      return;
    }

    if (data.matches.length === 1) {
      const student = data.matches[0];
      this.stateByChat.set(chatId, { flow: "assignment_topic", student });
      await this.sendText(message, `Selected ${student.name} (${student.course_name}).\nWhat topic was taught?`);
      return;
    }

    this.stateByChat.set(chatId, {
      flow: "assignment_pick",
      candidates: data.matches,
    });
    const options = data.matches
      .map((student, index) => `${index + 1}. ${student.name} | ${student.course_name}`)
      .join("\n");
    await this.sendText(message, `Multiple matches found.\n${options}\nReply with the number.`);
  }

  async handleAssignmentPick(message, chatId, text) {
    const state = this.stateByChat.get(chatId);
    const pickedIndex = Number.parseInt(text, 10) - 1;
    if (!state || Number.isNaN(pickedIndex) || pickedIndex < 0 || pickedIndex >= state.candidates.length) {
      await this.sendText(message, "Reply with a valid option number.");
      return;
    }

    const student = state.candidates[pickedIndex];
    this.stateByChat.set(chatId, { flow: "assignment_topic", student });
    await this.sendText(message, `Selected ${student.name} (${student.course_name}).\nWhat topic was taught?`);
  }

  async handleAssignmentTopic(message, chatId, text) {
    const state = this.stateByChat.get(chatId);
    if (!state || !state.student) {
      this.clear(chatId);
      await this.sendText(message, "Assignment session expired. Send `assignment` to start again.");
      return;
    }

    await this.sendText(message, "Generating assignment with Gemini...");
    const { data } = await this.api.post("/assignment/generate", {
      student: state.student,
      topic: text,
    });

    this.stateByChat.set(chatId, {
      flow: "assignment_confirm",
      student: state.student,
      topic: text,
      draft: data.assignment,
    });

    await this.sendText(message, this.formatAssignmentPreview(state.student, text, data.assignment));
  }

  async handleAssignmentConfirm(message, chatId, text) {
    const state = this.stateByChat.get(chatId);
    if (!state) {
      this.clear(chatId);
      await this.sendText(message, "Assignment session expired. Send `assignment` to start again.");
      return;
    }

    if (text === "cancel") {
      this.clear(chatId);
      await this.sendText(message, "Assignment workflow cancelled.");
      return;
    }

    if (text === "regenerate") {
      await this.sendText(message, "Regenerating assignment...");
      const { data } = await this.api.post("/assignment/generate", {
        student: state.student,
        topic: state.topic,
      });
      state.draft = data.assignment;
      this.stateByChat.set(chatId, state);
      await this.sendText(message, this.formatAssignmentPreview(state.student, state.topic, state.draft));
      return;
    }

    if (text !== "confirm") {
      await this.sendText(message, "Reply with `CONFIRM`, `REGENERATE`, or `CANCEL`.");
      return;
    }

    const { data } = await this.api.post("/assignment/deploy", {
      students: [state.student],
      assignment: state.draft,
    });
    this.clear(chatId);
    await this.sendText(
      message,
      data.success
        ? `Assignment deployed successfully to ${state.student.name}.`
        : `Assignment deployment failed with HTTP ${data.status_code}.`
    );
  }

  async handleCommand(message, command, whatsappAuthenticated) {
    const chatId = message.from;

    if (command === "help") {
      await this.sendText(
        message,
        [
          "*Available Commands*",
          "login",
          "attendance",
          "fetchstudents",
          "assignment",
          "status",
          "help",
        ].join("\n")
      );
      return;
    }

    if (command === "login") {
      await this.sendText(message, "Refreshing Nice Web login session...");
      const { data } = await this.api.post("/auth/login");
      await this.sendText(message, data.message);
      return;
    }

    if (command === "fetchstudents") {
      await this.sendText(message, "Fetching student cache in parallel...");
      const { data } = await this.api.post("/students/fetch");
      await this.sendText(
        message,
        `Student sync completed.\nStudents: ${data.total_students}\nCourses: ${data.total_courses}\nErrors: ${data.errors.length}\nDuration: ${data.duration_seconds}s`
      );
      return;
    }

    if (command === "status") {
      const { data } = await this.api.post("/status", {
        whatsapp_authenticated: whatsappAuthenticated,
      });
      await this.sendText(message, this.getStatusSummary(data));
      return;
    }

    if (command === "attendance") {
      await this.handleAttendanceEntry(message, chatId);
      return;
    }

    if (command === "assignment") {
      await this.handleAssignmentEntry(message, chatId);
      return;
    }

    await this.sendText(message, "Unknown command. Send `help` to see the available options.");
  }

  async handleMessage(message, whatsappAuthenticated) {
    const chatId = message.from;
    const text = (message.body || "").trim();
    const normalized = text.toLowerCase();
    const state = this.stateByChat.get(chatId);

    if (!state) {
      await this.handleCommand(message, normalized, whatsappAuthenticated);
      return;
    }

    if (state.flow === "attendance_mode") {
      await this.handleAttendanceMode(message, chatId, normalized);
      return;
    }

    if (state.flow === "attendance_manual") {
      await this.handleAttendanceManual(message, chatId, normalized);
      return;
    }

    if (state.flow === "assignment_search") {
      await this.handleAssignmentSearch(message, chatId, text);
      return;
    }

    if (state.flow === "assignment_pick") {
      await this.handleAssignmentPick(message, chatId, normalized);
      return;
    }

    if (state.flow === "assignment_topic") {
      await this.handleAssignmentTopic(message, chatId, text);
      return;
    }

    if (state.flow === "assignment_confirm") {
      await this.handleAssignmentConfirm(message, chatId, normalized);
      return;
    }

    this.clear(chatId);
    await this.sendText(message, "State reset. Send your command again.");
  }
}

module.exports = {
  ConversationManager,
};
