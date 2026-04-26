class FlowStateStore {
  constructor({ ttlMs }) {
    this.ttlMs = ttlMs;
    this.stateByChat = new Map();
  }

  get(chatId) {
    const current = this.stateByChat.get(chatId);
    if (!current) {
      return { state: null, expired: false };
    }

    const now = Date.now();
    if (current.expiresAt <= now) {
      this.stateByChat.delete(chatId);
      return { state: null, expired: true };
    }

    const refreshed = {
      ...current,
      updatedAt: now,
      expiresAt: now + this.ttlMs,
    };
    this.stateByChat.set(chatId, refreshed);
    return { state: refreshed, expired: false };
  }

  set(chatId, nextState) {
    const existing = this.stateByChat.get(chatId);
    const now = Date.now();
    const storedState = {
      chatId,
      currentFlow: nextState.currentFlow || existing?.currentFlow || "idle",
      currentStep: nextState.currentStep || existing?.currentStep || "main_menu",
      data: nextState.data || existing?.data || {},
      createdAt: existing?.createdAt || now,
      updatedAt: now,
      expiresAt: now + this.ttlMs,
    };
    this.stateByChat.set(chatId, storedState);
    return storedState;
  }

  update(chatId, updater) {
    const existing = this.stateByChat.get(chatId);
    if (!existing) {
      return null;
    }

    const nextState = typeof updater === "function" ? updater(existing) : updater;
    return this.set(chatId, {
      ...existing,
      ...nextState,
      data: nextState?.data || existing.data,
    });
  }

  clear(chatId) {
    this.stateByChat.delete(chatId);
  }
}

module.exports = {
  FlowStateStore,
};
