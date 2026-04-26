const {
  assignmentCandidatesPrompt,
  assignmentPreview,
  assignmentSearchPrompt,
  assignmentTopicPrompt,
  attendanceModeMenu,
  attendanceStudentPrompt,
  helpMessage,
  mainMenu,
  statusMessage,
} = require("../templates/messages");
const { logBackendRelay, logWhatsAppInfo } = require("../logging");

const ROOT_NUMBER_ACTIONS = {
  "1": "login",
  "2": "attendance",
  "3": "fetch_students",
  "4": "assignment",
  "5": "status",
  "6": "help",
  "7": "logout",
  "8": "refresh_session",
  "9": "restart",
};

const ROOT_TEXT_ACTIONS = {
  menu: "menu",
  start: "menu",
  hi: "menu",
  login: "login",
  attendance: "attendance",
  fetchstudents: "fetch_students",
  assignment: "assignment",
  status: "status",
  help: "help",
  logout: "logout",
  refreshsession: "refresh_session",
  refresh: "refresh_session",
  restart: "restart",
  restartcurrentflow: "restart",
};

const FLOW_TEXT_ACTIONS = {
  menu: "menu",
  start: "menu",
  hi: "menu",
  help: "help",
  status: "status",
  logout: "logout",
  refreshsession: "refresh_session",
  refresh: "refresh_session",
  restart: "restart",
  restartcurrentflow: "restart",
  cancel: "restart",
};

class AdminPanelController {
  constructor({ backendClient, stateStore }) {
    this.backendClient = backendClient;
    this.stateStore = stateStore;
  }

  normalizeInput(text) {
    const raw = String(text || "").trim();
    const lowered = raw.toLowerCase();
    return {
      raw,
      lowered,
      commandKey: lowered.replace(/[^a-z0-9]+/g, ""),
    };
  }

  async reply(message, text) {
    await message.reply(text);
  }

  resolveRootAction(input) {
    return ROOT_NUMBER_ACTIONS[input.raw] || ROOT_TEXT_ACTIONS[input.commandKey] || null;
  }

  resolveFlowAction(input) {
    if (input.raw === "9") {
      return "restart";
    }
    return FLOW_TEXT_ACTIONS[input.commandKey] || null;
  }

  resolveAttendanceMode(input) {
    if (input.raw === "1" || input.commandKey === "allpresent" || input.commandKey === "all") {
      return "all_present";
    }
    if (input.raw === "2" || input.commandKey === "manualattendance" || input.commandKey === "manualmode" || input.commandKey === "manual") {
      return "manual";
    }
    return null;
  }

  resolveAttendanceChoice(input) {
    if (input.raw === "1" || input.commandKey === "present" || input.commandKey === "p") {
      return "present";
    }
    if (input.raw === "2" || input.commandKey === "absent" || input.commandKey === "a") {
      return "absent";
    }
    if (input.raw === "3" || input.commandKey === "skip" || input.commandKey === "s") {
      return "skip";
    }
    return null;
  }

  resolveAssignmentConfirmChoice(input) {
    if (input.raw === "1" || input.commandKey === "confirm" || input.commandKey === "confirmandsend") {
      return "confirm";
    }
    if (input.raw === "2" || input.commandKey === "regenerate") {
      return "regenerate";
    }
    if (input.raw === "3" || input.commandKey === "cancel") {
      return "cancel";
    }
    return null;
  }

  async sendMainMenu(message, prefixText = "") {
    const payload = prefixText ? `${prefixText}\n\n${mainMenu()}` : mainMenu();
    await this.reply(message, payload);
  }

  async startAttendanceFlow(message, chatId) {
    this.stateStore.set(chatId, {
      currentFlow: "attendance",
      currentStep: "attendance_mode",
      data: {},
    });
    await this.reply(message, attendanceModeMenu());
  }

  async startAssignmentFlow(message, chatId) {
    this.stateStore.set(chatId, {
      currentFlow: "assignment",
      currentStep: "assignment_search",
      data: {},
    });
    await this.reply(message, assignmentSearchPrompt());
  }

  async runLogin(message) {
    await this.reply(message, "Starting NiceWeb login...");
    const result = await this.backendClient.login();
    logBackendRelay("auth.login", "NiceWeb login completed via Node panel.");
    await this.reply(message, result.message);
  }

  async runFetchStudents(message) {
    await this.reply(message, "Refreshing student cache...");
    const result = await this.backendClient.fetchStudents();
    logBackendRelay("students.fetch", "Student cache refresh completed via Node panel.", {
      totalStudents: result.total_students,
      totalCourses: result.total_courses,
      errors: Array.isArray(result.errors) ? result.errors.length : 0,
    });
    await this.reply(
      message,
      [
        result.message || "Student cache refreshed successfully.",
        `Students: ${result.total_students}`,
        `Courses: ${result.total_courses}`,
        `Errors: ${Array.isArray(result.errors) ? result.errors.length : 0}`,
        `Duration: ${result.duration_seconds}s`,
        `Last Sync Time: ${result.last_sync_time}`,
      ].join("\n")
    );
  }

  async runStatus(message, runtimeState) {
    const result = await this.backendClient.status(runtimeState.whatsappAuthenticated);
    await this.reply(message, statusMessage(result));
  }

  async runLogout(message, chatId) {
    this.stateStore.clear(chatId);
    await this.reply(message, "Clearing persisted NiceWeb session...");
    const result = await this.backendClient.logout();
    logBackendRelay("session.logout", "NiceWeb session cleared via Node panel.");
    await this.reply(message, result.message);
  }

  async runRefreshSession(message) {
    await this.reply(message, "Refreshing NiceWeb session...");
    const result = await this.backendClient.refreshSession();
    logBackendRelay("session.refresh", "NiceWeb session refreshed via Node panel.");
    await this.reply(message, result.message);
  }

  async performRootAction(message, action, runtimeState) {
    const chatId = message.from;

    switch (action) {
      case "menu":
        this.stateStore.clear(chatId);
        await this.sendMainMenu(message);
        return;
      case "login":
        await this.runLogin(message);
        return;
      case "attendance":
        await this.startAttendanceFlow(message, chatId);
        return;
      case "fetch_students":
        await this.runFetchStudents(message);
        return;
      case "assignment":
        await this.startAssignmentFlow(message, chatId);
        return;
      case "status":
        await this.runStatus(message, runtimeState);
        return;
      case "help":
        await this.reply(message, helpMessage());
        return;
      case "logout":
        await this.runLogout(message, chatId);
        return;
      case "refresh_session":
        await this.runRefreshSession(message);
        return;
      case "restart":
        this.stateStore.clear(chatId);
        await this.sendMainMenu(message, "Current flow restarted.");
        return;
      default:
        await this.sendMainMenu(message, "Invalid input. Reply with a valid menu number.");
    }
  }

  async resendCurrentPrompt(message, state) {
    if (!state) {
      await this.sendMainMenu(message);
      return;
    }

    if (state.currentStep === "attendance_mode") {
      await this.reply(message, attendanceModeMenu());
      return;
    }

    if (state.currentStep === "attendance_manual") {
      const student = state.data.students[state.data.index];
      await this.reply(
        message,
        attendanceStudentPrompt(student, state.data.index + 1, state.data.students.length)
      );
      return;
    }

    if (state.currentStep === "assignment_search") {
      await this.reply(message, assignmentSearchPrompt());
      return;
    }

    if (state.currentStep === "assignment_pick") {
      await this.reply(message, assignmentCandidatesPrompt(state.data.candidates));
      return;
    }

    if (state.currentStep === "assignment_topic") {
      await this.reply(message, assignmentTopicPrompt(state.data.student));
      return;
    }

    if (state.currentStep === "assignment_confirm") {
      await this.reply(
        message,
        assignmentPreview(state.data.student, state.data.topic, state.data.draft)
      );
      return;
    }

    await this.sendMainMenu(message);
  }

  async handleActiveGlobalAction(message, flowAction, runtimeState, state) {
    const chatId = message.from;

    if (flowAction === "menu") {
      this.stateStore.clear(chatId);
      await this.sendMainMenu(message);
      return true;
    }

    if (flowAction === "restart") {
      this.stateStore.clear(chatId);
      await this.sendMainMenu(message, "Current flow restarted.");
      return true;
    }

    if (flowAction === "help") {
      await this.reply(message, helpMessage(state));
      await this.resendCurrentPrompt(message, state);
      return true;
    }

    if (flowAction === "status") {
      await this.runStatus(message, runtimeState);
      await this.resendCurrentPrompt(message, state);
      return true;
    }

    if (flowAction === "refresh_session") {
      await this.runRefreshSession(message);
      await this.resendCurrentPrompt(message, state);
      return true;
    }

    if (flowAction === "logout") {
      await this.runLogout(message, chatId);
      await this.sendMainMenu(message);
      return true;
    }

    return false;
  }

  async handleAttendanceMode(message, chatId, input) {
    const choice = this.resolveAttendanceMode(input);
    if (!choice) {
      await this.reply(message, `Invalid input.\n\n${attendanceModeMenu()}`);
      return;
    }

    if (choice === "all_present") {
      await this.reply(message, "Submitting attendance for all students...");
      const result = await this.backendClient.markAllPresent();
      this.stateStore.clear(chatId);
      await this.reply(
        message,
        [
          result.message || "Attendance completed.",
          `Total: ${result.total}`,
          `Succeeded: ${result.succeeded}`,
          `Failed: ${result.failed}`,
        ].join("\n")
      );
      return;
    }

    await this.reply(message, "Loading student list for manual attendance...");
    const payload = await this.backendClient.startManualAttendance();
    this.stateStore.set(chatId, {
      currentFlow: "attendance",
      currentStep: "attendance_manual",
      data: {
        students: payload.students,
        index: 0,
        results: {
          present: 0,
          absent: 0,
          skipped: 0,
        },
      },
    });
    await this.reply(message, attendanceStudentPrompt(payload.students[0], 1, payload.students.length));
  }

  async handleAttendanceManual(message, chatId, state, input) {
    const choice = this.resolveAttendanceChoice(input);
    if (!choice) {
      const currentStudent = state.data.students[state.data.index];
      await this.reply(
        message,
        `Invalid input.\n\n${attendanceStudentPrompt(currentStudent, state.data.index + 1, state.data.students.length)}`
      );
      return;
    }

    const currentStudent = state.data.students[state.data.index];

    if (choice === "skip") {
      const nextResults = {
        ...state.data.results,
        skipped: state.data.results.skipped + 1,
      };
      const nextIndex = state.data.index + 1;

      if (nextIndex >= state.data.students.length) {
        this.stateStore.clear(chatId);
        await this.reply(
          message,
          [
            "Attendance completed successfully.",
            `Present: ${nextResults.present}`,
            `Absent: ${nextResults.absent}`,
            `Skipped: ${nextResults.skipped}`,
          ].join("\n")
        );
        return;
      }

      this.stateStore.set(chatId, {
        currentFlow: "attendance",
        currentStep: "attendance_manual",
        data: {
          ...state.data,
          index: nextIndex,
          results: nextResults,
        },
      });
      await this.reply(message, attendanceStudentPrompt(state.data.students[nextIndex], nextIndex + 1, state.data.students.length));
      return;
    }

    const statusLabel = choice === "present" ? "present" : "absent";
    const result = await this.backendClient.markAttendance(currentStudent, statusLabel);
    const nextResults = {
      ...state.data.results,
      [choice]: state.data.results[choice] + 1,
    };
    const nextIndex = state.data.index + 1;

    await this.reply(message, result.message || `${currentStudent.name} marked ${statusLabel}.`);

    if (nextIndex >= state.data.students.length) {
      this.stateStore.clear(chatId);
      await this.reply(
        message,
        [
          "Attendance completed successfully.",
          `Present: ${nextResults.present}`,
          `Absent: ${nextResults.absent}`,
          `Skipped: ${nextResults.skipped}`,
        ].join("\n")
      );
      return;
    }

    this.stateStore.set(chatId, {
      currentFlow: "attendance",
      currentStep: "attendance_manual",
      data: {
        ...state.data,
        index: nextIndex,
        results: nextResults,
      },
    });
    await this.reply(message, attendanceStudentPrompt(state.data.students[nextIndex], nextIndex + 1, state.data.students.length));
  }

  async handleAssignmentSearch(message, chatId, input) {
    if (!input.raw) {
      await this.reply(message, "Please send a student name, student ID, or batch keyword.");
      return;
    }

    const payload = await this.backendClient.searchStudents(input.raw);
    if (!Array.isArray(payload.matches) || payload.matches.length === 0) {
      await this.reply(message, "No students found. Try another search.");
      return;
    }

    if (payload.matches.length === 1) {
      const student = payload.matches[0];
      this.stateStore.set(chatId, {
        currentFlow: "assignment",
        currentStep: "assignment_topic",
        data: {
          student,
        },
      });
      await this.reply(message, assignmentTopicPrompt(student));
      return;
    }

    this.stateStore.set(chatId, {
      currentFlow: "assignment",
      currentStep: "assignment_pick",
      data: {
        candidates: payload.matches,
      },
    });
    await this.reply(message, assignmentCandidatesPrompt(payload.matches));
  }

  async handleAssignmentPick(message, chatId, state, input) {
    const selectedIndex = Number.parseInt(input.raw, 10) - 1;
    if (
      Number.isNaN(selectedIndex)
      || selectedIndex < 0
      || selectedIndex >= state.data.candidates.length
    ) {
      await this.reply(message, `Invalid input.\n\n${assignmentCandidatesPrompt(state.data.candidates)}`);
      return;
    }

    const student = state.data.candidates[selectedIndex];
    this.stateStore.set(chatId, {
      currentFlow: "assignment",
      currentStep: "assignment_topic",
      data: {
        student,
      },
    });
    await this.reply(message, assignmentTopicPrompt(student));
  }

  async handleAssignmentTopic(message, chatId, state, input) {
    if (!input.raw) {
      await this.reply(message, "Please send the topic taught today.");
      return;
    }

    await this.reply(message, "Generating Gemini draft assignment preview...");
    const payload = await this.backendClient.generateAssignment(state.data.student, input.raw);
    this.stateStore.set(chatId, {
      currentFlow: "assignment",
      currentStep: "assignment_confirm",
      data: {
        student: state.data.student,
        topic: input.raw,
        draft: payload.assignment,
      },
    });
    await this.reply(message, assignmentPreview(state.data.student, input.raw, payload.assignment));
  }

  async handleAssignmentConfirm(message, chatId, state, input) {
    const choice = this.resolveAssignmentConfirmChoice(input);
    if (!choice) {
      await this.reply(
        message,
        `Invalid input.\n\n${assignmentPreview(state.data.student, state.data.topic, state.data.draft)}`
      );
      return;
    }

    if (choice === "cancel") {
      this.stateStore.clear(chatId);
      await this.reply(message, "Assignment flow cancelled.");
      return;
    }

    if (choice === "regenerate") {
      await this.reply(message, "Regenerating Gemini draft...");
      const payload = await this.backendClient.generateAssignment(state.data.student, state.data.topic);
      this.stateStore.set(chatId, {
        currentFlow: "assignment",
        currentStep: "assignment_confirm",
        data: {
          ...state.data,
          draft: payload.assignment,
        },
      });
      await this.reply(message, assignmentPreview(state.data.student, state.data.topic, payload.assignment));
      return;
    }

    const result = await this.backendClient.deployAssignment(state.data.student, state.data.draft);
    this.stateStore.clear(chatId);
    await this.reply(message, result.message || "Assignment deployed successfully.");
  }

  async handleFlowMessage(message, chatId, state, input, runtimeState) {
    const flowAction = this.resolveFlowAction(input);
    if (flowAction) {
      const handled = await this.handleActiveGlobalAction(message, flowAction, runtimeState, state);
      if (handled) {
        return;
      }
    }

    if (state.currentStep === "attendance_mode") {
      await this.handleAttendanceMode(message, chatId, input);
      return;
    }

    if (state.currentStep === "attendance_manual") {
      await this.handleAttendanceManual(message, chatId, state, input);
      return;
    }

    if (state.currentStep === "assignment_search") {
      await this.handleAssignmentSearch(message, chatId, input);
      return;
    }

    if (state.currentStep === "assignment_pick") {
      await this.handleAssignmentPick(message, chatId, state, input);
      return;
    }

    if (state.currentStep === "assignment_topic") {
      await this.handleAssignmentTopic(message, chatId, state, input);
      return;
    }

    if (state.currentStep === "assignment_confirm") {
      await this.handleAssignmentConfirm(message, chatId, state, input);
      return;
    }

    this.stateStore.clear(chatId);
    await this.sendMainMenu(message, "State reset because the flow was no longer valid.");
  }

  async handleMessage(message, runtimeState) {
    const chatId = message.from;
    const input = this.normalizeInput(message.body);
    const { state, expired } = this.stateStore.get(chatId);

    if (expired) {
      logWhatsAppInfo("state.expired", "Conversation state expired and was reset.", {
        chatId,
      });
    }

    if (!state) {
      const rootAction = this.resolveRootAction(input);
      if (!rootAction) {
        await this.sendMainMenu(
          message,
          expired
            ? "Previous flow expired. Starting fresh."
            : "Welcome to the admin panel."
        );
        return;
      }

      await this.performRootAction(message, rootAction, runtimeState);
      return;
    }

    await this.handleFlowMessage(message, chatId, state, input, runtimeState);
  }
}

module.exports = {
  AdminPanelController,
};
