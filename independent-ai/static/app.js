"use strict";

(() => {
  const $ = (id) => document.getElementById(id);
  // Authentication and workspace content live only in this page's memory.
  const state = { authenticated: false, setup: false, token: "", cloudOnly: true, downloadsEnabled: false, tab: "chat", messages: [], files: [], status: null, sending: false, uploading: false, session: 0, fileRequest: 0, toastTimer: null };
  const MAX_FILE_BYTES = 25 * 1024 * 1024;
  const ICON_NS = "http://www.w3.org/2000/svg";
  let noteReturnFocus = null;

  function icon(name) {
    const svg = document.createElementNS(ICON_NS, "svg");
    svg.classList.add("icon");
    svg.setAttribute("aria-hidden", "true");
    const use = document.createElementNS(ICON_NS, "use");
    use.setAttribute("href", `#i-${name}`);
    svg.append(use);
    return svg;
  }

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function notice(message, error = false) {
    clearTimeout(state.toastTimer);
    const toast = $("toast");
    toast.textContent = message;
    toast.classList.toggle("error", error);
    toast.hidden = false;
    $("announcement").textContent = message;
    state.toastTimer = setTimeout(() => { toast.hidden = true; }, error ? 9000 : 5500);
  }

  function errorMessage(data, fallback) {
    if (typeof data?.detail === "string") return data.detail;
    if (typeof data?.error === "string") return data.error;
    if (Array.isArray(data?.detail)) return data.detail.map((item) => item.msg || "Invalid request").join(". ");
    return fallback;
  }

  async function api(path, options = {}) {
    const request = { credentials: "same-origin", cache: "no-store", ...options };
    if (state.token) request.headers = { ...request.headers, Authorization: `Bearer ${state.token}` };
    if (request.json !== undefined) {
      request.headers = { "Content-Type": "application/json", ...request.headers };
      request.body = JSON.stringify(request.json);
      delete request.json;
    }
    let response;
    try { response = await fetch(path, request); }
    catch { throw new Error("Cannot reach your workspace. Check the server connection and try again."); }
    let data = null;
    if (response.status !== 204) {
      try { data = await response.json(); } catch { /* Handled through response status. */ }
    }
    if (!response.ok) {
      if (response.status === 401 && state.authenticated) showAuth(false);
      throw new Error(errorMessage(data, response.status === 401 ? "Your session has ended. Please sign in again." : `The request could not be completed (${response.status}).`));
    }
    return data;
  }

  function formatBytes(value) {
    const bytes = Number(value) || 0;
    if (!bytes) return "0 B";
    if (bytes < 1024) return `${bytes} B`;
    const units = ["KB", "MB", "GB", "TB"];
    const power = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)) - 1, units.length - 1);
    const amount = bytes / (1024 ** (power + 1));
    return `${amount >= 100 ? amount.toFixed(0) : amount >= 10 ? amount.toFixed(1).replace(/\.0$/, "") : amount.toFixed(2).replace(/\.?0+$/, "")} ${units[power]}`;
  }

  function formatDate(value) {
    if (!value) return "—";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "—";
    return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", year: "numeric" }).format(date);
  }

  function showAuth(setup) {
    state.authenticated = false;
    state.token = "";
    state.downloadsEnabled = false;
    state.setup = setup;
    state.session += 1;
    state.sending = false;
    state.messages = [];
    state.files = [];
    state.status = null;
    if ($("cloud-note-dialog").open) $("cloud-note-dialog").close();
    $("cloud-note-form").reset();
    $("messages").replaceChildren();
    $("file-list").replaceChildren();
    $("chat-input").value = "";
    $("boot-view").hidden = true;
    $("app-view").hidden = true;
    $("auth-view").hidden = false;
    $("auth-title").textContent = setup ? "Make yourself at home." : "Welcome back.";
    $("auth-description").textContent = setup ? "Create a password to start your private workspace." : "Enter your password to open your Haven.";
    $("password-help").textContent = setup ? "Use at least 12 characters. Keep this password somewhere safe." : "Your password protects access to this workspace.";
    $("password").minLength = setup ? 12 : 1;
    $("password").autocomplete = state.cloudOnly ? "off" : setup ? "new-password" : "current-password";
    $("confirm-password").autocomplete = state.cloudOnly ? "off" : "new-password";
    $("session-note").hidden = !state.cloudOnly;
    $("password").value = "";
    $("confirm-password").value = "";
    $("confirm-password").required = setup;
    $("confirm-password-wrap").hidden = !setup;
    $("auth-submit").firstElementChild.textContent = setup ? "Create workspace" : "Open workspace";
    $("auth-error").hidden = true;
    $("auth-submit").disabled = false;
    updateComposer();
    setTimeout(() => { if (!state.authenticated) $("password").focus(); }, 40);
  }

  async function boot() {
    $("boot-view").hidden = false;
    $("boot-retry").hidden = true;
    $("boot-view").querySelector("p").textContent = "Opening your workspace…";
    try {
      const session = await api("/api/session");
      state.cloudOnly = session.cloud_only !== false;
      if (session.authenticated) await enterWorkspace();
      else showAuth(Boolean(session.setup_required));
    } catch (error) {
      $("boot-view").querySelector("p").textContent = error.message;
      $("boot-retry").hidden = false;
    }
  }

  async function enterWorkspace() {
    state.authenticated = true;
    state.session += 1;
    const session = state.session;
    $("password").value = "";
    $("confirm-password").value = "";
    $("auth-view").hidden = true;
    $("boot-view").hidden = true;
    $("app-view").hidden = false;
    switchTab("chat");
    const results = await Promise.allSettled([refreshStatus(), refreshMessages()]);
    if (session !== state.session) return;
    for (const result of results) if (result.status === "rejected") notice(result.reason.message, true);
    $("chat-input").focus();
  }

  async function refreshStatus() {
    const session = state.session;
    const status = await api("/api/status");
    if (session !== state.session) return;
    state.status = status;
    const hadDownloads = state.downloadsEnabled;
    if (typeof status.client?.cloud_only === "boolean") state.cloudOnly = status.client.cloud_only;
    state.downloadsEnabled = !state.cloudOnly && status.client?.downloads_enabled === true;
    const storage = status.storage || {};
    const used = Number(storage.used_bytes) || 0;
    const quota = Number(storage.quota_bytes) || 0;
    const percent = quota > 0 ? Math.min(100, Math.max(0, used / quota * 100)) : 0;
    $("file-count").textContent = String(storage.file_count || 0);
    $("trash-count").textContent = String(storage.trash_count || 0);
    $("storage-percent").textContent = `${Math.round(percent)}%`;
    $("storage-meter").setAttribute("aria-valuenow", String(Math.round(percent)));
    $("storage-meter").firstElementChild.style.width = `${percent}%`;
    $("storage-description").textContent = `${formatBytes(used)} of ${formatBytes(quota)} used`;
    const isOllama = status.assistant?.mode === "ollama";
    $("assistant-mode-label").textContent = isOllama ? "Server AI assistant" : "Server knowledge assistant";
    $("assistant-mode-detail").textContent = isOllama ? (status.assistant.model || "Runs through server Ollama") : "Find answers in your cloud-stored text files";
    $("composer-mode").textContent = isOllama ? "AI runs on the server" : "Uses your server-stored text files";
    $("composer-note").textContent = isOllama ? "AI can make mistakes. Check important answers and their sources." : "This assistant retrieves relevant passages, with sources. Verify important information.";
    $("connection-label").textContent = status.assistant?.ready === false ? "Assistant unavailable" : "Processed on server";
    if (hadDownloads !== state.downloadsEnabled) {
      renderMessages();
      if (state.tab !== "chat") renderFiles(state.tab === "trash");
    }
    updateComposer();
  }

  async function refreshMessages() {
    const session = state.session;
    const data = await api("/api/messages");
    if (session !== state.session) return;
    state.messages = Array.isArray(data.messages) ? data.messages : [];
    renderMessages();
  }

  function createMessage(message) {
    const user = message.role === "user";
    const row = element("article", `message ${user ? "user" : "assistant"}`);
    const avatar = element("div", "message-avatar", user ? "YOU" : "✧");
    avatar.setAttribute("aria-hidden", "true");
    const body = element("div", "message-body");
    const label = element("div", "message-label", user ? "You" : "Haven");
    if (message.created_at) {
      const date = new Date(message.created_at);
      if (!Number.isNaN(date.getTime())) {
        const time = element("time", "", new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(date));
        time.dateTime = date.toISOString();
        label.append(time);
      }
    }
    body.append(label, element("div", "message-content", message.content || ""));
    if (Array.isArray(message.sources) && message.sources.length) {
      const sources = element("div", "message-sources");
      message.sources.forEach((source, index) => {
        const details = element("details", "source");
        details.append(element("summary", "", `${index + 1}. ${source.name || "Source file"}`));
        const content = element("div", "source-content");
        content.append(element("p", "", source.excerpt || ""));
        if (source.id && state.downloadsEnabled) {
          const link = element("a", "", "Download source file");
          link.href = `/api/files/${encodeURIComponent(source.id)}/download`;
          link.setAttribute("download", "");
          content.append(link);
        } else content.append(element("span", "source-storage-note", "Source file stays on the cloud server."));
        details.append(content);
        sources.append(details);
      });
      body.append(sources);
    }
    row.append(avatar, body);
    return row;
  }

  function renderMessages() {
    $("messages").replaceChildren(...state.messages.map(createMessage));
    $("chat-empty").hidden = state.messages.length > 0 || state.sending;
    $("clear-chat").disabled = state.messages.length === 0 || state.sending;
    if (state.sending) {
      const row = element("article", "message assistant");
      const avatar = element("div", "message-avatar", "✧");
      avatar.setAttribute("aria-hidden", "true");
      const body = element("div", "message-body");
      body.append(element("div", "message-label", "Haven"));
      const thinking = element("div", "thinking");
      thinking.setAttribute("aria-label", "Finding an answer");
      for (let i = 0; i < 3; i += 1) thinking.append(element("span"));
      body.append(thinking);
      row.append(avatar, body);
      $("messages").append(row);
    }
    requestAnimationFrame(() => { $("chat-scroll").scrollTop = $("chat-scroll").scrollHeight; });
  }

  function updateComposer() {
    $("send-message").disabled = !state.authenticated || state.sending || !$("chat-input").value.trim() || state.status?.assistant?.ready === false;
    $("chat-input").disabled = state.sending;
    $("clear-chat").disabled = state.sending || state.messages.length === 0;
  }

  function resizeComposer() {
    $("chat-input").style.height = "auto";
    $("chat-input").style.height = `${Math.min(150, $("chat-input").scrollHeight)}px`;
    updateComposer();
  }

  function switchTab(tab) {
    if (!["chat", "files", "trash"].includes(tab)) return;
    state.tab = tab;
    for (const button of document.querySelectorAll("[data-tab]")) {
      const current = button.dataset.tab === tab;
      button.classList.toggle("active", current);
      if (current) button.setAttribute("aria-current", "page"); else button.removeAttribute("aria-current");
    }
    $("chat-page").hidden = tab !== "chat";
    $("files-page").hidden = tab === "chat";
    $("breadcrumb-current").textContent = tab === "chat" ? "Assistant" : tab === "files" ? "My files" : "Trash";
    if (tab !== "chat") {
      const trash = tab === "trash";
      $("files-title").textContent = trash ? "Trash" : "My files";
      $("files-eyebrow").textContent = trash ? "A SECOND CHANCE FOR YOUR FILES" : "A PLACE FOR WHAT MATTERS";
      $("files-subtitle").textContent = trash ? "Changed your mind? Your files are still here." : "Keep your knowledge together. Make it easier to find.";
      $("upload-button").hidden = trash;
      $("create-cloud-note").hidden = trash;
      $("upload-zone").hidden = trash;
      $("indexing-note").hidden = trash;
      $("trash-note").hidden = !trash;
      $("date-heading").textContent = trash ? "Trashed" : "Added";
      document.querySelector(".file-table").classList.toggle("trash-table", trash);
      $("file-list-label").textContent = trash ? "Files in Trash" : "Your files";
      refreshFiles().catch((error) => notice(error.message, true));
    }
  }

  async function refreshFiles() {
    const request = ++state.fileRequest;
    const session = state.session;
    const trash = state.tab === "trash";
    $("refresh-files").disabled = true;
    try {
      const data = await api(`/api/files?trash=${trash}`);
      if (session !== state.session || request !== state.fileRequest) return;
      state.files = Array.isArray(data.files) ? data.files : [];
      renderFiles(trash);
    } finally {
      if (request === state.fileRequest) $("refresh-files").disabled = false;
    }
  }

  function renderFiles(trash) {
    const rows = state.files.map((file) => {
      const row = element("tr");
      const nameCell = element("td");
      const nameWrap = element("div", "file-name-cell");
      const fileIcon = element("span", "file-type-icon");
      fileIcon.append(icon("files"));
      const nameText = element("div");
      const name = element("span", "file-name", file.name);
      const extension = String(file.name || "").split(".");
      nameText.append(name, element("span", "file-extension", extension.length > 1 ? extension.pop().slice(0, 10) + " file" : "File"));
      nameWrap.append(fileIcon, nameText);
      nameCell.append(nameWrap);
      const size = element("td", "size-cell", formatBytes(file.size));
      const date = element("td", "date-cell", formatDate(trash ? file.trashed_at : file.created_at));
      const indexed = element("td", "status-cell");
      const badge = element("span", `index-badge${file.indexed && !trash ? "" : " stored"}`);
      if (file.indexed && !trash) badge.append(icon("check"));
      badge.append(document.createTextNode(trash ? "Not in search" : file.indexed ? "Searchable" : "Stored only"));
      badge.title = file.index_note || (file.indexed ? "Available to your assistant on the server" : "Stored on the server; not indexed for search");
      indexed.append(badge);
      const actionsCell = element("td");
      const actions = element("div", "file-actions");
      if (state.downloadsEnabled) {
        const download = element("a", "icon-button");
        download.href = `/api/files/${encodeURIComponent(file.id)}/download`;
        download.setAttribute("download", "");
        download.title = `Download ${file.name}`;
        download.setAttribute("aria-label", download.title);
        download.append(icon("download"));
        actions.append(download);
      }
      const action = element("button", trash ? "restore-button" : "icon-button", trash ? "Restore" : undefined);
      action.type = "button";
      action.title = `${trash ? "Restore" : "Move to Trash:"} ${file.name}`;
      action.setAttribute("aria-label", action.title);
      if (!trash) action.append(icon("trash"));
      action.addEventListener("click", () => changeFile(file, trash ? "restore" : "trash", action));
      actions.append(action);
      if (trash) {
        const purge = element("button", "icon-button purge-button");
        purge.type = "button";
        purge.title = `Delete ${file.name} forever`;
        purge.setAttribute("aria-label", purge.title);
        purge.append(icon("trash"));
        purge.addEventListener("click", () => {
          if (window.confirm(`Delete “${file.name}” forever? This cannot be undone. Quotes already saved in chat history remain until you clear the chat.`)) changeFile(file, "purge", purge);
        });
        actions.append(purge);
      }
      actionsCell.append(actions);
      row.append(nameCell, size, date, indexed, actionsCell);
      return row;
    });
    $("file-list").replaceChildren(...rows);
    $("files-empty").hidden = rows.length > 0;
    $("files-empty").querySelector("h2").textContent = trash ? "Nothing in Trash. A fresh start." : "No files yet. Room for plenty.";
    $("files-empty").querySelector("p").textContent = trash ? "Files you move to Trash will appear here." : "Upload something to make this space your own.";
    $("file-list-label").textContent = `${trash ? "Files in Trash" : "Your files"} · ${rows.length}`;
  }

  async function changeFile(file, action, button) {
    if (button.disabled) return;
    button.disabled = true;
    const session = state.session;
    try {
      await api(`/api/files/${encodeURIComponent(file.id)}/${action}`, { method: "POST", json: action === "purge" ? { confirm: true } : {} });
      if (session !== state.session) return;
      const results = await Promise.allSettled([refreshFiles(), refreshStatus()]);
      for (const result of results) if (result.status === "rejected") notice(result.reason.message, true);
      notice(action === "trash" ? `“${file.name}” moved to Trash.` : action === "purge" ? `“${file.name}” deleted forever.` : `“${file.name}” restored.`);
    } catch (error) { notice(error.message, true); }
    finally { button.disabled = false; }
  }

  function chooseFiles() {
    if (state.uploading || !state.authenticated) return;
    $("file-input").click();
  }

  async function uploadFiles(files) {
    if (state.uploading || !files.length || !state.authenticated) return;
    const accepted = Array.from(files).filter((file) => file.size <= MAX_FILE_BYTES);
    const rejected = files.length - accepted.length;
    if (rejected) notice(`${rejected} ${rejected === 1 ? "file is" : "files are"} larger than 25 MB and could not be uploaded.`, true);
    if (!accepted.length) return;
    state.uploading = true;
    const session = state.session;
    $("upload-button").disabled = true;
    $("browse-files").disabled = true;
    $("chat-add-file").disabled = true;
    $("empty-upload").disabled = true;
    $("create-cloud-note").disabled = true;
    const failures = [];
    let uploaded = 0;
    try {
      for (let index = 0; index < accepted.length; index += 1) {
        if (session !== state.session) break;
        $("upload-button").querySelector("span").textContent = `Uploading ${index + 1}/${accepted.length}…`;
        $("announcement").textContent = `Uploading file ${index + 1} of ${accepted.length}.`;
        const body = new FormData();
        body.append("file", accepted[index]);
        try { await api("/api/files", { method: "POST", body }); uploaded += 1; }
        catch (error) { failures.push(`${accepted[index].name}: ${error.message}`); }
      }
      if (session !== state.session) return;
      if (state.tab !== "chat") {
        if (state.tab === "trash") switchTab("files");
        else await refreshFiles();
      }
      await refreshStatus();
      if (failures.length) notice(`${uploaded ? `${uploaded} uploaded. ` : ""}${failures.join(" ")}`, true);
      else if (uploaded) notice(`${uploaded === 1 ? "File uploaded" : `${uploaded} files uploaded`}. Check My files to see which files are searchable.`);
    } catch (error) { notice(error.message, true); }
    finally {
      state.uploading = false;
      $("file-input").value = "";
      $("upload-button").disabled = false;
      $("upload-button").querySelector("span").textContent = "Upload files";
      $("browse-files").disabled = false;
      $("chat-add-file").disabled = false;
      $("empty-upload").disabled = false;
      $("create-cloud-note").disabled = false;
    }
    return { uploaded, failures };
  }

  function setNoteBusy(busy) {
    for (const id of ["cloud-note-name", "cloud-note-content", "cloud-note-save", "cloud-note-cancel"]) $(id).disabled = busy;
    $("cloud-note-save").textContent = busy ? "Saving…" : "Save to cloud";
  }

  $("create-cloud-note").addEventListener("click", () => {
    if (state.uploading || !state.authenticated) return;
    noteReturnFocus = document.activeElement;
    $("cloud-note-error").hidden = true;
    setNoteBusy(false);
    $("cloud-note-dialog").showModal();
  });
  $("cloud-note-cancel").addEventListener("click", () => {
    if (!state.uploading) $("cloud-note-dialog").close();
  });
  $("cloud-note-dialog").addEventListener("cancel", (event) => {
    if (state.uploading) event.preventDefault();
  });
  $("cloud-note-dialog").addEventListener("close", () => {
    $("cloud-note-form").reset();
    $("cloud-note-error").hidden = true;
    if (state.authenticated && noteReturnFocus?.isConnected) noteReturnFocus.focus();
    noteReturnFocus = null;
  });
  $("cloud-note-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (state.uploading || !state.authenticated) return;
    let name = $("cloud-note-name").value.trim();
    const content = $("cloud-note-content").value;
    $("cloud-note-error").hidden = true;
    if (!name || !content.trim()) {
      $("cloud-note-error").textContent = "Give your note a name and some text before saving.";
      $("cloud-note-error").hidden = false;
      (!name ? $("cloud-note-name") : $("cloud-note-content")).focus();
      return;
    }
    name = name.replace(/[\\/\u0000-\u001f]/g, "-");
    if (!/\.(md|txt)$/i.test(name)) name += ".md";
    if (name.length > 180) {
      const extension = /\.txt$/i.test(name) ? ".txt" : ".md";
      name = name.slice(0, 180 - extension.length) + extension;
    }
    setNoteBusy(true);
    const file = new File([content], name, { type: "text/plain;charset=utf-8" });
    try {
      const result = await uploadFiles([file]);
      if (!state.authenticated) return;
      if (result?.uploaded === 1) $("cloud-note-dialog").close();
      else {
        $("cloud-note-error").textContent = "The note could not be saved. Your draft is still here; check the error message and try again.";
        $("cloud-note-error").hidden = false;
      }
    } finally {
      setNoteBusy(false);
    }
  });

  $("auth-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if ($("auth-submit").disabled) return;
    $("auth-error").hidden = true;
    const password = $("password").value;
    if (state.setup && password !== $("confirm-password").value) {
      $("auth-error").textContent = "The passwords do not match. Please try again.";
      $("auth-error").hidden = false;
      $("confirm-password").focus();
      return;
    }
    $("auth-submit").disabled = true;
    const label = $("auth-submit").firstElementChild;
    label.textContent = state.setup ? "Creating workspace…" : "Opening workspace…";
    try {
      const auth = await api(state.setup ? "/api/setup" : "/api/login", { method: "POST", json: { password } });
      state.token = typeof auth?.token === "string" ? auth.token : "";
      if (state.cloudOnly && !state.token) throw new Error("The server did not issue a cloud session. Please try signing in again.");
      await enterWorkspace();
    } catch (error) {
      $("auth-error").textContent = error.message;
      $("auth-error").hidden = false;
      $("password").value = "";
      $("confirm-password").value = "";
      $("password").focus();
    } finally {
      $("auth-submit").disabled = false;
      label.textContent = state.setup ? "Create workspace" : "Open workspace";
    }
  });

  $("logout").addEventListener("click", async () => {
    $("logout").disabled = true;
    try {
      await api("/api/logout", { method: "POST", json: {} });
      $("toast").hidden = true;
    } catch (error) { notice(error.message, true); }
    finally { showAuth(false); $("logout").disabled = false; }
  });

  $("chat-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = $("chat-input").value.trim();
    if (!message || state.sending || !state.authenticated || state.status?.assistant?.ready === false) return;
    const session = state.session;
    state.sending = true;
    state.messages.push({ role: "user", content: message, created_at: new Date().toISOString() });
    $("chat-input").value = "";
    resizeComposer();
    renderMessages();
    $("announcement").textContent = "Your assistant is finding an answer.";
    try {
      const result = await api("/api/chat", { method: "POST", json: { message } });
      if (session !== state.session) return;
      if (result.message) state.messages.push(result.message);
      else await refreshMessages();
    } catch (error) {
      if (session !== state.session) return;
      notice(error.message, true);
      try { await refreshMessages(); } catch { state.messages.pop(); }
      $("chat-input").value = message;
    } finally {
      if (session === state.session) {
        state.sending = false;
        renderMessages();
        resizeComposer();
        $("chat-input").focus();
      }
    }
  });

  $("chat-input").addEventListener("input", resizeComposer);
  $("chat-input").addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      if (!$("send-message").disabled) $("chat-form").requestSubmit();
    }
  });

  $("clear-chat").addEventListener("click", async () => {
    if (state.sending || !state.messages.length || !window.confirm("Clear this conversation? Your files will stay in your workspace.")) return;
    const session = state.session;
    $("clear-chat").disabled = true;
    try {
      await api("/api/messages/clear", { method: "POST", json: {} });
      if (session !== state.session) return;
      state.messages = [];
      renderMessages();
      notice("Conversation cleared. A fresh page for your next idea.");
    } catch (error) { notice(error.message, true); }
    finally { updateComposer(); }
  });

  for (const button of document.querySelectorAll("[data-tab]")) button.addEventListener("click", () => switchTab(button.dataset.tab));
  for (const button of document.querySelectorAll("[data-prompt]")) button.addEventListener("click", () => {
    $("chat-input").value = button.dataset.prompt;
    resizeComposer();
    $("chat-input").focus();
  });
  for (const id of ["upload-button", "browse-files", "chat-add-file", "empty-upload"]) $(id).addEventListener("click", chooseFiles);
  $("file-input").addEventListener("change", () => uploadFiles($("file-input").files));
  $("refresh-files").addEventListener("click", () => refreshFiles().catch((error) => notice(error.message, true)));
  $("boot-retry").addEventListener("click", boot);
  for (const name of ["dragenter", "dragover"]) $("upload-zone").addEventListener(name, (event) => {
    event.preventDefault();
    if (!state.uploading) $("upload-zone").classList.add("drag-over");
  });
  for (const name of ["dragleave", "drop"]) $("upload-zone").addEventListener(name, (event) => {
    event.preventDefault();
    $("upload-zone").classList.remove("drag-over");
  });
  $("upload-zone").addEventListener("drop", (event) => uploadFiles(event.dataTransfer.files));
  // Prevent dropped files outside the upload area from navigating away from the workspace.
  window.addEventListener("dragover", (event) => { if (event.dataTransfer?.types.includes("Files")) event.preventDefault(); });
  window.addEventListener("drop", (event) => { if (event.dataTransfer?.types.includes("Files")) event.preventDefault(); });

  boot();
})();
