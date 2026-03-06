/* AntiGrav Access – College ERP JavaScript */

// ── Theme ──
function toggleTheme() {
    const html = document.documentElement;
    const next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
    updateThemeIcon(next);
}
function updateThemeIcon(theme) {
    document.querySelectorAll('#theme-icon, #theme-icon-auth').forEach(i => {
        if (i) i.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    });
}
(function () {
    const saved = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', saved);
    document.addEventListener('DOMContentLoaded', () => updateThemeIcon(saved));
})();

// ── Toast ──
function showToast(msg, type = 'info') {
    const c = document.getElementById('toast-container'); if (!c) return;
    const t = document.createElement('div');
    t.className = 'toast ' + type;
    const icons = { success: 'check-circle', error: 'exclamation-circle', info: 'info-circle' };
    t.innerHTML = '<i class="fas fa-' + (icons[type] || 'info-circle') + '"></i> ' + msg;
    c.appendChild(t);
    setTimeout(() => { t.style.opacity = '0'; t.style.transform = 'translateX(80px)'; setTimeout(() => t.remove(), 300); }, 4000);
}

// ── Auth ──
function logout() {
    fetch('/api/auth/logout', { method: 'POST' }).catch(() => { });
    document.cookie = 'access_token=; Max-Age=0; path=/';
    window.location.href = '/login';
}

async function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById('email').value;
    const pass = document.getElementById('password').value;
    const err = document.getElementById('login-error');
    const btn = document.getElementById('login-btn');
    err.classList.remove('show');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner" style="width:18px;height:18px;margin:0;border-width:2px"></span>';
    try {
        const fd = new URLSearchParams(); fd.append('username', email); fd.append('password', pass);
        const res = await fetch('/api/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: fd, credentials: 'same-origin' });
        if (!res.ok) { const d = await res.json().catch(() => ({})); throw new Error(d.detail || 'Invalid credentials'); }
        showToast('Login successful!', 'success');
        setTimeout(() => window.location.href = '/dashboard', 500);
    } catch (ex) {
        err.textContent = ex.message; err.classList.add('show');
        btn.disabled = false; btn.innerHTML = 'Sign in <i class="fas fa-arrow-right"></i>';
    }
}

// ── API helpers ──
async function api(url, opts = {}) {
    const res = await fetch(url, { credentials: 'same-origin', headers: { 'Accept': 'application/json' }, ...opts });
    if (res.status === 401) { window.location.href = '/login'; return null; }
    return res;
}
async function apiJson(url, opts = {}) {
    const r = await api(url, opts); if (!r) return null;
    if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || 'Request failed'); }
    return r.json();
}
function setText(id, val) { const el = document.getElementById(id); if (el) el.textContent = val; }

// ═══════════════════════════════════════════════
// DASHBOARD
// ═══════════════════════════════════════════════
async function loadStudentDashboard() {
    try {
        const data = await apiJson('/api/threshold/my-status');
        if (!data || !data.subjects) return;
        const subjects = data.subjects;

        // Summary cards
        const cardsEl = document.getElementById('threshold-cards');
        if (!cardsEl) return;
        const totalSubjects = subjects.length;
        const belowCount = subjects.filter(s => !s.above_threshold).length;
        const avgPct = totalSubjects > 0 ? Math.round(subjects.reduce((a, s) => a + s.percentage, 0) / totalSubjects) : 0;

        cardsEl.innerHTML = `
      <div class="stat-card"><div class="stat-card-header"><span>Enrolled Subjects</span><div class="stat-icon blue"><i class="fas fa-book"></i></div></div><div class="stat-value">${totalSubjects}</div></div>
      <div class="stat-card"><div class="stat-card-header"><span>Average Attendance</span><div class="stat-icon ${avgPct >= 75 ? 'green' : 'red'}"><i class="fas fa-percentage"></i></div></div><div class="stat-value">${avgPct}%</div><div class="stat-progress"><div class="stat-progress-bar" style="width:${avgPct}%"></div></div></div>
      <div class="stat-card"><div class="stat-card-header"><span>Below 75%</span><div class="stat-icon red"><i class="fas fa-exclamation-triangle"></i></div></div><div class="stat-value">${belowCount}</div><div class="stat-sub">Subjects at risk</div></div>
    `;

        // Subject table
        const tb = document.getElementById('threshold-tbody');
        if (!tb) return;
        if (!subjects.length) { tb.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:32px;color:var(--text-muted);">No subjects enrolled yet</td></tr>'; return; }
        tb.innerHTML = subjects.map(s => {
            const cls = s.above_threshold ? 'green' : 'red';
            const badge = s.above_threshold ? '<span class="badge badge-green"><i class="fas fa-circle"></i> Safe</span>' : '<span class="badge badge-red"><i class="fas fa-circle"></i> At Risk</span>';
            let action = '';
            if (s.above_threshold) action = `<span style="color:var(--green);">Can skip ${s.days_off} class${s.days_off !== 1 ? 'es' : ''}</span>`;
            else action = `<span style="color:var(--red);">Need ${s.days_needed} more class${s.days_needed !== 1 ? 'es' : ''}</span>`;
            return `<tr>
        <td><strong>${s.subject_name}</strong><br><small style="color:var(--text-muted)">${s.subject_code}</small></td>
        <td>${s.classes_attended}</td><td>${s.classes_conducted}</td>
        <td><div class="confidence-bar"><span style="color:var(--${cls})">${s.percentage}%</span><div class="confidence-track"><div class="confidence-fill" style="width:${s.percentage}%;background:var(--${cls})"></div></div></div></td>
        <td>${badge}</td><td>${action}</td></tr>`;
        }).join('');
    } catch (ex) { console.error('Student dashboard error:', ex); }
}

async function loadFacultyDashboard() {
    try {
        const subjects = await apiJson('/api/subjects/');
        setText('fac-subjects', subjects ? subjects.length : 0);
        const threshold = await apiJson('/api/threshold/students?filter=below');
        const belowStudents = threshold?.students || [];
        setText('fac-below', belowStudents.length);
        const tb = document.getElementById('fac-below-tbody');
        if (!tb) return;
        if (!belowStudents.length) { tb.innerHTML = '<tr><td colspan="6" style="text-align:center;padding:32px;color:var(--text-muted);">All students are above threshold! 🎉</td></tr>'; return; }
        tb.innerHTML = belowStudents.map(s => `<tr>
      <td>${s.student_name}</td><td>${s.enrollment_no}</td><td>${s.subject_name} (${s.subject_code})</td>
      <td>${s.classes_attended}</td><td>${s.classes_conducted}</td>
      <td><span style="color:var(--red);font-weight:700;">${s.percentage}%</span></td></tr>`).join('');
    } catch (ex) { console.error('Faculty dashboard error:', ex); }
}

async function loadAdminDashboard() {
    try {
        const users = await apiJson('/api/users/?limit=1000').catch(() => []);
        const subjects = await apiJson('/api/subjects/').catch(() => []);
        const threshold = await apiJson('/api/threshold/students?filter=below').catch(() => ({ students: [] }));
        const studentCount = Array.isArray(users) ? users.filter(u => u.role === 'Student').length : 0;
        const facultyCount = Array.isArray(users) ? users.filter(u => u.role === 'Faculty').length : 0;
        setText('admin-total', studentCount);
        setText('admin-faculty', facultyCount);
        setText('admin-subjects', Array.isArray(subjects) ? subjects.length : 0);
        setText('admin-below', threshold?.students?.length || 0);
    } catch (ex) { console.error('Admin dashboard error:', ex); }
}

// ═══════════════════════════════════════════════
// SUBJECTS PAGE
// ═══════════════════════════════════════════════
let _enrollSubjectId = null;

function showAddSubjectModal() {
    document.getElementById('add-subject-form').style.display = 'block';
    loadFacultyDropdown();
}

async function loadFacultyDropdown() {
    try {
        const users = await apiJson('/api/users/?limit=500');
        const faculty = (users || []).filter(u => u.role === 'Faculty');
        const sel = document.getElementById('sub-faculty');
        if (!sel) return;
        sel.innerHTML = '<option value="">Select Faculty</option>' + faculty.map(f => `<option value="${f.id}">${f.first_name} ${f.last_name} (${f.employee_id})</option>`).join('');
    } catch (ex) { }
}

async function createSubject() {
    const code = document.getElementById('sub-code').value;
    const name = document.getElementById('sub-name').value;
    if (!code || !name) { showToast('Code and Name are required', 'error'); return; }
    try {
        await apiJson('/api/subjects/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                code, name,
                department: document.getElementById('sub-dept').value || null,
                semester: parseInt(document.getElementById('sub-sem').value) || null,
                total_classes: parseInt(document.getElementById('sub-total').value) || 40,
                faculty_id: parseInt(document.getElementById('sub-faculty').value) || null,
            })
        });
        showToast('Subject created!', 'success');
        document.getElementById('add-subject-form').style.display = 'none';
        loadSubjectsPage();
    } catch (ex) { showToast(ex.message, 'error'); }
}

async function deleteSubject(id) {
    if (!confirm('Delete this subject and all its records?')) return;
    try {
        await apiJson('/api/subjects/' + id, { method: 'DELETE' });
        showToast('Subject deleted', 'success');
        loadSubjectsPage();
    } catch (ex) { showToast(ex.message, 'error'); }
}

async function showEnrollForm(subjectId, subjectName) {
    _enrollSubjectId = subjectId;
    document.getElementById('enroll-subject-name').textContent = subjectName;
    document.getElementById('enroll-form').style.display = 'block';
    try {
        const users = await apiJson('/api/users/?limit=500');
        const students = (users || []).filter(u => u.role === 'Student');
        const enrolled = await apiJson('/api/subjects/' + subjectId + '/students');
        const enrolledIds = new Set((enrolled || []).map(e => e.id));
        const el = document.getElementById('student-checkboxes');
        if (!students.length) { el.innerHTML = '<p style="color:var(--text-muted)">No students found. Create student accounts first.</p>'; return; }
        el.innerHTML = students.map(s => `<label style="display:flex;align-items:center;gap:8px;padding:6px 0;cursor:pointer;">
      <input type="checkbox" value="${s.id}" ${enrolledIds.has(s.id) ? 'checked' : ''}>
      <span>${s.first_name} ${s.last_name} (${s.employee_id})</span></label>`).join('');
    } catch (ex) { showToast('Failed to load students', 'error'); }
}

async function submitEnrollment() {
    const checks = document.querySelectorAll('#student-checkboxes input:checked');
    const ids = Array.from(checks).map(c => parseInt(c.value));
    if (!ids.length) { showToast('Select at least one student', 'error'); return; }
    try {
        await apiJson('/api/subjects/' + _enrollSubjectId + '/enroll', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ student_ids: ids })
        });
        showToast('Students enrolled!', 'success');
        document.getElementById('enroll-form').style.display = 'none';
        loadSubjectsPage();
    } catch (ex) { showToast(ex.message, 'error'); }
}

async function loadSubjectsPage() {
    const tb = document.getElementById('subjects-tbody'); if (!tb) return;
    try {
        const subjects = await apiJson('/api/subjects/');
        if (!subjects || !subjects.length) { tb.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:32px;color:var(--text-muted);">No subjects yet</td></tr>'; return; }
        const isAdmin = document.querySelector('[data-role="admin"]') !== null || document.querySelector('a[href="/add-user"]') !== null;
        const isStudent = !isAdmin && document.querySelector('a[href="/threshold"]')?.textContent?.includes('Tracker');
        tb.innerHTML = subjects.map(s => {
            let actions = '';
            if (isAdmin || document.querySelector('a[href="/admin"]')) {
                actions = `<td>
          <button class="btn btn-sm btn-primary" onclick="showEnrollForm(${s.id},'${s.name}')"><i class="fas fa-user-plus"></i></button>
          <button class="btn btn-sm btn-danger" onclick="deleteSubject(${s.id})"><i class="fas fa-trash"></i></button></td>`;
            }
            let attendance = '';
            return `<tr><td><strong>${s.code}</strong></td><td>${s.name}</td><td>${s.department || '–'}</td><td>${s.semester || '–'}</td><td>${s.faculty_name || 'Unassigned'}</td><td>${s.enrolled_count}</td>${actions}${attendance}</tr>`;
        }).join('');
    } catch (ex) { console.error(ex); }
}

// ═══════════════════════════════════════════════
// MARK SUBJECT ATTENDANCE
// ═══════════════════════════════════════════════
async function loadSubjectDropdown() {
    try {
        const subjects = await apiJson('/api/subjects/');
        const sel = document.getElementById('att-subject'); if (!sel) return;
        sel.innerHTML = '<option value="">Select Subject</option>' + (subjects || []).map(s => `<option value="${s.id}">${s.code} – ${s.name}</option>`).join('');
        // Set today's date
        const dateInput = document.getElementById('att-date');
        if (dateInput) dateInput.value = new Date().toISOString().split('T')[0];
    } catch (ex) { console.error(ex); }
}

async function loadStudentsForAttendance() {
    const subjectId = document.getElementById('att-subject').value;
    const area = document.getElementById('students-attendance-area');
    if (!subjectId) { area.style.display = 'none'; return; }
    area.style.display = 'block';
    try {
        const students = await apiJson('/api/subjects/' + subjectId + '/students');
        const tb = document.getElementById('att-students-tbody'); if (!tb) return;
        if (!students || !students.length) { tb.innerHTML = '<tr><td colspan="3" style="text-align:center;padding:24px;color:var(--text-muted);">No students enrolled</td></tr>'; return; }
        tb.innerHTML = students.map(s => `<tr>
      <td>${s.enrollment_no}</td><td>${s.name}</td>
      <td><select class="form-input" data-student="${s.id}" style="width:120px;padding:6px 10px;font-size:0.85rem;">
        <option value="Present">Present</option><option value="Absent">Absent</option><option value="Late">Late</option>
      </select></td></tr>`).join('');
    } catch (ex) { showToast('Failed to load students', 'error'); }
}

function markAll(status) {
    document.querySelectorAll('#att-students-tbody select').forEach(s => s.value = status);
}

async function submitSubjectAttendance() {
    const subjectId = document.getElementById('att-subject').value;
    const attDate = document.getElementById('att-date').value;
    if (!subjectId || !attDate) { showToast('Select subject and date', 'error'); return; }
    const selects = document.querySelectorAll('#att-students-tbody select');
    const entries = Array.from(selects).map(s => ({ student_id: parseInt(s.dataset.student), status: s.value }));
    if (!entries.length) { showToast('No students to mark', 'error'); return; }
    try {
        await apiJson('/api/subjects/' + subjectId + '/attendance', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date: attDate, entries })
        });
        showToast(`Attendance marked for ${entries.length} students!`, 'success');
    } catch (ex) { showToast(ex.message, 'error'); }
}

// ═══════════════════════════════════════════════
// THRESHOLD PAGE
// ═══════════════════════════════════════════════
async function loadStudentThreshold() {
    const container = document.getElementById('student-threshold-cards'); if (!container) return;
    try {
        const data = await apiJson('/api/threshold/my-status');
        if (!data || !data.subjects || !data.subjects.length) {
            container.innerHTML = '<div class="card" style="text-align:center;padding:40px;"><i class="fas fa-book" style="font-size:2rem;color:var(--text-muted);margin-bottom:12px;"></i><p style="color:var(--text-muted);">No subjects enrolled yet. Contact your admin.</p></div>';
            return;
        }
        container.innerHTML = '<div class="threshold-cards-grid">' + data.subjects.map(s => {
            const cls = s.above_threshold ? 'above' : 'below';
            let actionClass, actionText;
            if (s.above_threshold && s.days_off > 5) { actionClass = 'safe'; actionText = `<i class="fas fa-check-circle"></i> You can skip <strong>${s.days_off}</strong> more classes and stay above 75%`; }
            else if (s.above_threshold) { actionClass = 'warning'; actionText = `<i class="fas fa-exclamation-triangle"></i> Only <strong>${s.days_off}</strong> skip${s.days_off !== 1 ? 's' : ''} left before you drop below 75%`; }
            else { actionClass = 'danger'; actionText = `<i class="fas fa-times-circle"></i> You need <strong>${s.days_needed}</strong> more class${s.days_needed !== 1 ? 'es' : ''} to reach 75%`; }

            return `<div class="threshold-card">
        <div class="threshold-card-header">
          <div><h4>${s.subject_name}</h4><div class="subject-code">${s.subject_code}</div></div>
          <div class="threshold-percentage ${cls}">${s.percentage}%</div>
        </div>
        <div class="threshold-progress"><div class="threshold-progress-bar ${cls}" style="width:${Math.min(100, s.percentage)}%"></div><div class="threshold-marker"></div></div>
        <div class="threshold-info">
          <div class="threshold-info-item"><div class="label">Attended</div><div class="value">${s.classes_attended}</div></div>
          <div class="threshold-info-item"><div class="label">Conducted</div><div class="value">${s.classes_conducted}</div></div>
          <div class="threshold-info-item"><div class="label">Total Scheduled</div><div class="value">${s.total_scheduled}</div></div>
          <div class="threshold-info-item"><div class="label">Days Off Left</div><div class="value">${s.days_off}</div></div>
        </div>
        <div class="threshold-action ${actionClass}">${actionText}</div>
      </div>`;
        }).join('') + '</div>';
    } catch (ex) { container.innerHTML = '<p style="color:var(--red);">Failed to load data</p>'; console.error(ex); }
}

async function loadThresholdReport(filter = '') {
    const tb = document.getElementById('threshold-report-tbody'); if (!tb) return;
    try {
        let url = '/api/threshold/students';
        if (filter) url += '?filter=' + filter;
        const data = await apiJson(url);
        const students = data?.students || [];
        if (!students.length) { tb.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:32px;color:var(--text-muted);">No records found</td></tr>'; return; }
        tb.innerHTML = students.map(s => {
            const badge = s.above_threshold ? '<span class="badge badge-green"><i class="fas fa-circle"></i> Above</span>' : '<span class="badge badge-red"><i class="fas fa-circle"></i> Below</span>';
            return `<tr><td>${s.student_name}</td><td>${s.enrollment_no}</td><td>${s.subject_name} (${s.subject_code})</td>
        <td>${s.classes_attended}</td><td>${s.classes_conducted}</td>
        <td><span style="color:${s.above_threshold ? 'var(--green)' : 'var(--red)'};font-weight:700;">${s.percentage}%</span></td>
        <td>${badge}</td></tr>`;
        }).join('');
    } catch (ex) { console.error(ex); }
}

function filterThreshold(filter) {
    document.querySelectorAll('#filter-all,#filter-below,#filter-above').forEach(b => b.classList.remove('active'));
    const btn = document.getElementById('filter-' + (filter || 'all'));
    if (btn) btn.classList.add('active');
    loadThresholdReport(filter === 'all' ? '' : filter);
}

// ═══════════════════════════════════════════════
// CAMERA (Face-based attendance, kept for admin)
// ═══════════════════════════════════════════════
let stream = null, capturedBlob = null;
async function startCamera(vidId) {
    const v = document.getElementById(vidId); if (!v) return;
    try {
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user', width: 640, height: 480 } });
        v.srcObject = stream; v.play();
        const ov = document.getElementById('camera-overlay'); if (ov) ov.classList.add('hidden');
        return true;
    } catch (e) { showToast('Camera access denied', 'error'); return false; }
}
function stopCamera() { if (stream) { stream.getTracks().forEach(t => t.stop()); stream = null; } }
function captureFrame(vidId) {
    const v = document.getElementById(vidId); if (!v || !stream) return null;
    const c = document.createElement('canvas'); c.width = v.videoWidth; c.height = v.videoHeight;
    c.getContext('2d').drawImage(v, 0, 0);
    return new Promise(r => c.toBlob(b => { capturedBlob = b; r(b); }, 'image/jpeg', 0.9));
}
async function captureAndRecognize() {
    const blob = await captureFrame('camera-video');
    if (!blob) { showToast('Start the camera first', 'error'); return; }
    stopCamera();
    const rd = document.getElementById('recognition-result');
    rd.innerHTML = '<div style="text-align:center;padding:20px;"><div class="spinner"></div><p style="color:var(--text-muted);">Analyzing face...</p></div>';
    try {
        const fd = new FormData(); fd.append('file', blob, 'capture.jpg');
        const res = await api('/api/attendance/mark', { method: 'POST', body: fd });
        const data = await res.json();
        if (res.ok) {
            rd.innerHTML = `<div class="result-content success"><i class="fas fa-check-circle" style="font-size:2rem;color:var(--green);margin-bottom:8px;"></i><h3>${data.user_name}</h3><p style="font-size:2rem;font-weight:800;color:var(--green);">${data.confidence}%</p><p>${data.entry_type} at ${new Date(data.timestamp).toLocaleTimeString()}</p><span class="badge badge-green" style="margin-top:8px;"><i class="fas fa-circle"></i> Attendance Marked</span></div>`;
            showToast('Attendance marked!', 'success');
        } else {
            rd.innerHTML = `<div class="result-content error"><i class="fas fa-exclamation-triangle" style="font-size:2rem;color:var(--red);margin-bottom:8px;"></i><h3>Not Recognized</h3><p>${data.detail || 'Face not in database'}</p></div>`;
        }
    } catch (ex) { showToast(ex.message || 'Recognition failed', 'error'); }
}
function resetAttendance() {
    const r = document.getElementById('recognition-result');
    if (r) r.innerHTML = '<div class="result-placeholder"><i class="fas fa-face-smile"></i><p>Position your face within the frame and click scan.</p></div>';
    capturedBlob = null; startCamera('camera-video');
}

// ── Face Upload ──
function previewFace(input) {
    const f = input.files[0]; if (!f) return;
    const circle = document.getElementById('upload-circle');
    if (circle) circle.innerHTML = '<img src="' + URL.createObjectURL(f) + '" alt="Preview">';
    document.getElementById('save-face-btn').disabled = false;
}
async function submitFaceUpload() {
    const input = document.getElementById('face-input');
    let file = input.files[0];
    if (!file && capturedBlob) file = new File([capturedBlob], 'capture.jpg', { type: 'image/jpeg' });
    if (!file) { showToast('Select an image first', 'error'); return; }
    const btn = document.getElementById('save-face-btn');
    btn.disabled = true; btn.innerHTML = '<span class="spinner" style="width:18px;height:18px;margin:0;border-width:2px"></span> Saving...';
    try {
        const fd = new FormData(); fd.append('file', file);
        const res = await api('/api/face/upload', { method: 'POST', body: fd });
        const data = await res.json();
        if (res.ok) {
            showToast('Face data saved!', 'success');
            document.getElementById('face-result').innerHTML = '<div class="alert alert-success"><i class="fas fa-check-circle"></i> Face enrolled</div>';
        } else showToast(data.detail || 'Upload failed', 'error');
    } catch (ex) { showToast(ex.message || 'Upload failed', 'error'); }
    btn.disabled = false; btn.innerHTML = '<i class="fas fa-check"></i> Save Face Data';
}

// ── Records ──
async function loadRecords(page = 1) {
    const from = document.getElementById('from-date')?.value || '';
    const to = document.getElementById('to-date')?.value || '';
    let url = '/api/records/?page=' + page + '&per_page=20';
    if (from) url += '&from_date=' + from; if (to) url += '&to_date=' + to;
    try { const d = await apiJson(url); if (d) renderRecords(d.records, 'records-tbody'); }
    catch (ex) { showToast('Failed to load records', 'error'); }
}
function renderRecords(records, tbodyId) {
    const tb = document.getElementById(tbodyId); if (!tb) return;
    if (!records || !records.length) { tb.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:32px;color:var(--text-muted);">No records found</td></tr>'; return; }
    tb.innerHTML = records.map(r => {
        const badge = r.is_late ? '<span class="badge badge-amber"><i class="fas fa-circle"></i> Late</span>' : '<span class="badge badge-green"><i class="fas fa-circle"></i> Present</span>';
        return `<tr><td>${r.date}</td><td>${r.time}</td><td><span class="badge badge-blue">${r.entry_type}</span></td><td><div class="confidence-bar"><span>${r.confidence_score}%</span><div class="confidence-track"><div class="confidence-fill" style="width:${r.confidence_score}%"></div></div></div></td><td>${badge}</td></tr>`;
    }).join('');
}
function exportRecords(fmt) {
    const from = document.getElementById('from-date')?.value || '';
    const to = document.getElementById('to-date')?.value || '';
    window.location.href = `/api/records/export/${fmt}?from_date=${from}&to_date=${to}`;
}

// ── Admin Panel ──
async function loadAdminStats() {
    try {
        const s = await apiJson('/api/admin/stats');
        if (s) {
            setText('admin-total', s.total_employees); setText('admin-present', s.present_today); setText('admin-absent', s.absent_today); setText('admin-rate', s.attendance_rate + '%');
            const bar = document.getElementById('admin-rate-bar'); if (bar) bar.style.width = s.attendance_rate + '%';
        }
        const d = await apiJson('/api/admin/departments');
        if (d && d.departments) {
            const tb = document.getElementById('dept-tbody');
            if (tb) tb.innerHTML = d.departments.map(dp => `<tr><td>${dp.department}</td><td>${dp.total_employees}</td><td>${dp.present_today}</td><td>${dp.attendance_rate}%</td></tr>`).join('');
        }
    } catch (ex) { console.error(ex); }
}

// ── Reconcile Attendance (faculty/admin) ──
async function reconcileAttendance() {
    const subjectId = document.getElementById('att-subject').value;
    const attDate = document.getElementById('att-date').value;
    if (!subjectId || !attDate) { showToast('Select subject and date first', 'error'); return; }
    try {
        const data = await apiJson(`/api/subjects/${subjectId}/reconcile?date_str=${attDate}`, { method: 'POST' });
        showToast(`Reconciled! Present: ${data.summary.present}, Absent: ${data.summary.absent}, Disputed (face only): ${data.summary.face_only}, Disputed (faculty only): ${data.summary.faculty_only}`, 'success');
    } catch (ex) { showToast(ex.message, 'error'); }
}

// ── Notification Badge Polling ──
async function pollNotifications() {
    try {
        const res = await fetch('/api/notifications/count', { credentials: 'same-origin' });
        if (!res.ok) return;
        const data = await res.json();
        const count = data.unread_count || 0;
        ['notifBadge', 'notifBadgeBell'].forEach(id => {
            const el = document.getElementById(id);
            if (el) { el.textContent = count; el.style.display = count > 0 ? 'flex' : 'none'; }
        });
    } catch (e) { /* ignore */ }
}

// ═══════════════════════════════════════════════
// INIT – Route based
// ═══════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
    const path = window.location.pathname;

    if (path === '/dashboard') {
        // Detect role from sidebar links
        if (document.querySelector('a[href="/admin"]')) loadAdminDashboard();
        else if (document.querySelector('a[href="/mark-subject-attendance"]')) loadFacultyDashboard();
        else loadStudentDashboard();
    }

    if (path === '/subjects') loadSubjectsPage();
    if (path === '/mark-subject-attendance') loadSubjectDropdown();

    if (path === '/threshold') {
        if (document.getElementById('student-threshold-cards')) loadStudentThreshold();
        else loadThresholdReport();
    }

    if (path === '/records') loadRecords();
    if (path === '/admin') loadAdminStats();
    if (path === '/mark-attendance') startCamera('camera-video');

    // Poll notifications every 30 seconds on all authenticated pages
    if (document.getElementById('notifBadge') || document.getElementById('notifBadgeBell')) {
        pollNotifications();
        setInterval(pollNotifications, 30000);
    }
});
