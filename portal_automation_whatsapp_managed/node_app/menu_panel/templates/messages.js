function mainMenu() {
  return [
    "=================================",
    "NiceWeb Admin Control Panel",
    "===========================",
    "",
    "1. Login",
    "2. Attendance",
    "3. Fetch Students",
    "4. Assignment",
    "5. Status",
    "6. Help",
    "7. Logout",
    "8. Refresh Session",
    "9. Restart Current Flow",
    "",
    "Reply with number only.",
  ].join("\n");
}

function helpMessage(state) {
  const currentStepLine = state
    ? `Current Flow: ${state.currentFlow} / ${state.currentStep}`
    : "Current Flow: Idle";
  return [
    "NiceWeb Admin Help",
    "==================",
    "",
    "Use menu numbers for the fastest flow.",
    "Text fallback also works: login, attendance, fetchstudents, assignment, status.",
    "Send menu, start, or hi to open the main menu.",
    "Send 9 any time to restart the current flow safely.",
    currentStepLine,
  ].join("\n");
}

function attendanceModeMenu() {
  return [
    "Attendance Mode",
    "",
    "1. All Present",
    "2. Manual Attendance",
    "",
    "Reply with number.",
  ].join("\n");
}

function attendanceStudentPrompt(student, position, total) {
  return [
    "Student:",
    student.name || "Unknown Student",
    "",
    `Progress: ${position}/${total}`,
    student.student_id ? `ID: ${student.student_id}` : null,
    student.batch ? `Batch: ${student.batch}` : null,
    "",
    "1. Present",
    "2. Absent",
    "3. Skip",
    "",
    "Reply with number.",
  ]
    .filter(Boolean)
    .join("\n");
}

function assignmentSearchPrompt() {
  return [
    "Assignment Mode",
    "",
    "Search student by:",
    "- student name",
    "- student ID",
    "- batch keyword",
    "",
    "Send your search text.",
  ].join("\n");
}

function assignmentCandidatesPrompt(students) {
  const options = students.map((student, index) => {
    const coursePart = student.course_name ? ` | ${student.course_name}` : "";
    return `${index + 1}. ${student.name}${coursePart}`;
  });

  return [
    "Students Found:",
    "",
    ...options,
    "",
    "Reply with number.",
  ].join("\n");
}

function assignmentTopicPrompt(student) {
  return [
    `Selected: ${student.name}`,
    student.course_name ? `Course: ${student.course_name}` : null,
    "",
    "Send topic taught today",
  ]
    .filter(Boolean)
    .join("\n");
}

function assignmentPreview(student, topic, draft) {
  const questions = Array.isArray(draft.questions)
    ? draft.questions.map((question, index) => `${index + 1}. ${question}`)
    : [];

  return [
    "Assignment Preview",
    "==================",
    "",
    `Student: ${student.name}`,
    student.course_name ? `Course: ${student.course_name}` : null,
    `Topic: ${topic}`,
    "",
    `Title: ${draft.title}`,
    `Description: ${draft.description}`,
    "",
    "Questions:",
    ...questions,
    "",
    "1. Confirm and Send",
    "2. Regenerate",
    "3. Cancel",
    "",
    "Reply with number.",
  ]
    .filter(Boolean)
    .join("\n");
}

function statusMessage(payload) {
  return [
    "NiceWeb Admin Status",
    "====================",
    "",
    `WhatsApp Status: ${payload.whatsapp_status}`,
    `Backend Status: ${payload.backend_status}`,
    `NiceWeb Login Status: ${payload.niceweb_login_status}`,
    `Student Cache Status: ${payload.student_cache_status}`,
    `Last Sync Time: ${payload.last_sync_time}`,
    `Gemini Status: ${payload.gemini_status}`,
  ].join("\n");
}

module.exports = {
  assignmentCandidatesPrompt,
  assignmentPreview,
  assignmentSearchPrompt,
  assignmentTopicPrompt,
  attendanceModeMenu,
  attendanceStudentPrompt,
  helpMessage,
  mainMenu,
  statusMessage,
};
