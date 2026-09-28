/**
 * Follow-ups Manager
 * Handles fetching, rendering, caching, and check-in success for follow-ups.
 * Filters out completed follow-ups so they never reappear after refresh.
 */

(function () {
  // === Configuration ===
  const LOCAL_CACHE_KEY = 'followups_cache_v1';
  const COMPLETED_STATUS_VALUE = 'completed';

  // === Utilities ===
  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  function nowTs() {
    return Date.now();
  }

  function escapeHtml(s) {
    if (!s) return '';
    return String(s).replace(/[&<>"']/g, function (m) {
      return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[m];
    });
  }

  // === In-memory state ===
  window.followups = window.followups || [];

  // === Parse helpers ===
  function parseFollowupLi(li) {
    if (!li) return null;
    const idAttr = li.id || li.getAttribute('data-followup-id') || '';
    let id = null;
    if (idAttr && idAttr.startsWith('followup-')) {
      id = idAttr.replace('followup-', '');
    } else if (li.getAttribute('data-followup-id')) {
      id = li.getAttribute('data-followup-id');
    }
    const status = (li.getAttribute('data-followup-status') || '').toLowerCase();
    const patientName = li.getAttribute('data-patient-name') || '';
    const scheduledDate = li.getAttribute('data-scheduled-date') || '';
    // store innerHTML so we can re-render the same markup
    const innerHTML = li.innerHTML;
    return {
      id: id,
      status: status,
      patient_name: patientName,
      scheduled_date: scheduledDate,
      html: innerHTML
    };
  }

  // === Local cache (localStorage) ===
  function saveFollowupsCache() {
    try {
      localStorage.setItem(LOCAL_CACHE_KEY, JSON.stringify(window.followups || []));
    } catch (e) {
      console.warn('Unable to save followups cache', e);
    }
  }

  function loadFollowupsCache() {
    try {
      const raw = localStorage.getItem(LOCAL_CACHE_KEY);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) return [];
      return parsed;
    } catch (e) {
      return [];
    }
  }

  // === Update follow-up buttons based on current state ===
  function updateFollowupButtons() {
    const pending = (window.followups || []).filter(f => String(f.status).toLowerCase() !== COMPLETED_STATUS_VALUE);
    
    // Group follow-ups by patient name (case-insensitive)
    const followupsByPatient = {};
    pending.forEach(f => {
      const patientName = (f.patient_name || '').toLowerCase();
      if (!followupsByPatient[patientName]) {
        followupsByPatient[patientName] = [];
      }
      followupsByPatient[patientName].push(f);
    });
    
    // Update all follow-up buttons
    document.querySelectorAll('.follow-btn').forEach(btn => {
      const patientId = btn.getAttribute('data-patient-id');
      if (!patientId) return;
      
      // Try to find patient name from the row
      const row = btn.closest('li');
      if (!row) return;
      const patientName = (row.getAttribute('data-name') || '').toLowerCase();
      
      const patientFollowups = followupsByPatient[patientName] || [];
      if (patientFollowups.length > 0) {
        btn.textContent = `Follow up (${patientFollowups.length})`;
        btn.disabled = true;
        btn.classList.add('scheduled');
      } else {
        btn.textContent = 'Follow up';
        btn.disabled = false;
        btn.classList.remove('scheduled');
      }
    });
  }

  // === Rendering ===
  function renderFollowupsFromState() {
    const followupsList = document.querySelector('#followups-list');
    if (!followupsList) return;
    followupsList.innerHTML = '';

    const pending = (window.followups || []).filter(f => String(f.status).toLowerCase() !== COMPLETED_STATUS_VALUE);
    if (pending.length === 0) {
      const empty = document.createElement('li');
      empty.id = 'empty-followups-msg';
      empty.textContent = 'No scheduled follow-ups';
      followupsList.appendChild(empty);
      return;
    }

    pending.forEach(f => {
      const li = document.createElement('li');
      li.id = `followup-${f.id}`;
      li.setAttribute('data-followup-status', f.status || '');
      if (f.patient_name) li.setAttribute('data-patient-name', f.patient_name);
      if (f.scheduled_date) li.setAttribute('data-scheduled-date', f.scheduled_date);
      // Use stored HTML if available; falls back to a minimal markup
      li.innerHTML = f.html || buildFollowupInnerHTML(f);
      followupsList.appendChild(li);
    });

    // Reattach check-in handlers for rendered elements
    attachCheckinHandlers();
    // Update follow-up buttons after rendering
    updateFollowupButtons();
  }

  function buildFollowupInnerHTML(f) {
    // Minimal fallback markup (used only if we didn't get server innerHTML)
    const patient = `<div class="followup-left"><strong>${escapeHtml(f.patient_name || '')}</strong></div>`;
    const right = `<div style="display:flex; align-items:center; gap:8px;"><span class="badge date-badge">${escapeHtml(f.scheduled_date || '')}</span><button class="btn small checkin-btn" data-followup-id="${f.id}">Check-in</button></div>`;
    return `<div class="followup-row">${patient}${right}</div>`;
  }

  // === State modifications ===
  function setFollowups(newList) {
    window.followups = newList || [];
    saveFollowupsCache();
  }

  function removeFollowupFromState(followupId) {
    if (!followupId) return;
    window.followups = (window.followups || []).filter(f => String(f.id) !== String(followupId));
    saveFollowupsCache();
  }

  // === Fetching followups ===
  // Parse the server-rendered followups-list from the current page or freshly fetched page
  async function fetchFollowupsByParsingPage() {
    try {
      // Fetch a fresh page snapshot to get the followups-list HTML (cache-busted)
      const url = window.location.pathname + (window.location.search ? '&' : '?') + '_=' + nowTs();
      const res = await fetch(url, { cache: 'no-store', credentials: 'same-origin' });
      const html = await res.text();
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, 'text/html');
      const newFollowupsList = doc.querySelector('#followups-list');

      if (!newFollowupsList) {
        // If page doesn't contain the list, also try current DOM
        const current = document.querySelector('#followups-list');
        if (!current) return;
        const items = Array.from(current.querySelectorAll('li'));
        const arr = itemsToFollowupObjects(items);
        setFollowups(arr);
        renderFollowupsFromState();
        return;
      }

      const items = Array.from(newFollowupsList.querySelectorAll('li'));
      const arr = itemsToFollowupObjects(items);
      setFollowups(arr);
      renderFollowupsFromState();
    } catch (err) {
      console.error('Failed to fetch/parse followups by page:', err);
      // as last resort, try to initialize from current DOM
      initFollowupsFromDOM();
    }
  }

  function itemsToFollowupObjects(items) {
    const arr = [];
    items.forEach(it => {
      if (it.id === 'empty-followups-msg') return;
      const f = parseFollowupLi(it);
      if (!f) return;
      // Exclude completed
      if (String(f.status).toLowerCase() === COMPLETED_STATUS_VALUE) return;
      arr.push(f);
    });
    return arr;
  }

  // Public loader that tries cache then fetches fresh
  async function loadFollowups() {
    // Try cached first to render immediately
    const cached = loadFollowupsCache();
    if (Array.isArray(cached) && cached.length > 0) {
      // render cached but still refresh from network
      window.followups = cached.filter(f => String(f.status).toLowerCase() !== COMPLETED_STATUS_VALUE);
      renderFollowupsFromState();
    } else {
      // Try to initialize from DOM server-rendered content for instant UI
      initFollowupsFromDOM();
    }

    // Fetch fresh data from server
    await fetchFollowupsByParsingPage();
  }

  // === Initialization helpers ===
  function initFollowupsFromDOM() {
    const followupsList = document.querySelector('#followups-list');
    if (!followupsList) return;
    const items = Array.from(followupsList.querySelectorAll('li'));
    const arr = itemsToFollowupObjects(items);
    window.followups = arr;
    saveFollowupsCache();
    renderFollowupsFromState();
  }

  // === Event handlers (check-in) ===
  function attachCheckinHandlers() {
    // delegate to current .checkin-btn elements
    document.querySelectorAll('.checkin-btn').forEach(btn => {
      // ensure we don't attach multiple times
      if (btn._checkinAttached) return;
      btn._checkinAttached = true;

      btn.addEventListener('click', async function (e) {
        e.preventDefault();
        const fid = this.getAttribute('data-followup-id') || (this.closest('li') && this.closest('li').id && this.closest('li').id.replace('followup-', ''));
        if (!fid) return;

        const csrftoken = getCookie('csrftoken');
        try {
          const formData = new FormData();
          formData.append('followup_id', fid);

          const res = await fetch(window.FOLLOWUP_CHECKIN_URL, {
            method: 'POST',
            headers: { 'X-CSRFToken': csrftoken },
            body: formData,
            credentials: 'same-origin',
            cache: 'no-store'
          });

          const data = await res.json();
          if (!data.success) {
            alert(data.error || 'Failed to record check-in');
            return;
          }

          try {
            const c = data.checkin || {};
            const pid = c.patient_id;
            if (pid) {
              const btn = document.querySelector(`.follow-btn[data-patient-id="${pid}"]`);
              if (btn) {
                // Check if there are any remaining scheduled follow-ups for this patient
                const remainingFollowups = (window.followups || []).filter(f => {
                  const fPatientName = (f.patient_name || '').toLowerCase();
                  const checkinPatientName = (c.patient_name || '').toLowerCase();
                  return fPatientName === checkinPatientName && String(f.status).toLowerCase() !== COMPLETED_STATUS_VALUE;
                });
                
                if (remainingFollowups.length === 0) {
                  // No more follow-ups, enable the button
                  btn.textContent = 'Follow up';
                  btn.disabled = false;
                  btn.classList.remove('scheduled');
                } else {
                  // Still has follow-ups, update count but keep disabled
                  btn.textContent = `Follow up (${remainingFollowups.length})`;
                  btn.disabled = true;
                  btn.classList.add('scheduled');
                }
              }
            }
          } catch (e) {}

          // 0) Immediately append the new check-in row to the Check-ins list
          try {
            const c = data.checkin;
            const checkinsList = document.querySelector('#checkins-list');
            if (c && checkinsList) {
              const statusClass = (c.status === 'early') ? 'badge--early' : (c.status === 'late') ? 'badge--late' : 'badge--normal';
              const doctorClass = (String(c.doctor_display || '').toLowerCase().includes('ami')) ? 'doctor-ami' : '';
              // Remove "No check-ins today" if present
              const emptyMsg = checkinsList.querySelector('#empty-checkins-msg');
              if (emptyMsg) { emptyMsg.remove(); }
              const li = document.createElement('li');
              li.setAttribute('data-patient-name', String(c.patient_name || '').toLowerCase());
              li.setAttribute('data-checkin-time', c.checkin_time_attr || '');
              li.innerHTML = `
                <div class="followup-row">
                  <div class="followup-left">
                    <strong>${escapeHtml(c.patient_name || '')}</strong>
                    <span class="badge ${doctorClass}">${escapeHtml(c.doctor_display || '')}</span>
                  </div>
                <div style="display:flex; align-items:center; gap:8px;">
                    <span class="badge date-badge">${escapeHtml(c.checkin_time_display || '')}</span>
                    <span class="badge ${statusClass}">${escapeHtml(c.status.replace('_',' ').replace(/\b\\w/g,s=>s.toUpperCase()) || '')}</span>
                </div>
              </div>`;
              // Prepend newest check-in
              checkinsList.insertBefore(li, checkinsList.firstChild);
              // Scroll to top to show latest
              checkinsList.scrollTop = 0;
            }
          } catch (e) {
            console.warn('Failed to inject immediate check-in row', e);
          }

          // 1) Remove the DOM row immediately
          const row = document.querySelector(`#followup-${fid}`);
          if (row) row.remove();

          // 2) Remove from in-memory state and localStorage so it won't reappear after refresh
          removeFollowupFromState(fid);

          // 2a) If this was the last pending follow-up, render the empty state immediately
          try {
            const pendingLeft = (window.followups || []).filter(f => String(f.status).toLowerCase() !== COMPLETED_STATUS_VALUE).length;
            if (pendingLeft === 0) {
              renderFollowupsFromState();
            }
          } catch (e) {
            console.warn('Failed to update empty follow-ups state', e);
          }

          // 3) Refresh check-ins card so the new check-in appears
          try { refreshCheckinsList(); } catch (e) { console.warn('refreshCheckinsList failed', e); }

          // 4) Refresh patient list fragment to update button states (non-full-page)
          try {
            const pRes = await fetch(window.location.pathname + (window.location.search ? '&' : '?') + '_=' + nowTs(), { cache: 'no-store', credentials: 'same-origin' });
            const pHtml = await pRes.text();
            const pDoc = new DOMParser().parseFromString(pHtml, 'text/html');
            const newListSection = pDoc.querySelector('#patientListSection');
            const currentListSection = document.querySelector('#patientListSection');
            if (newListSection && currentListSection) {
              currentListSection.innerHTML = newListSection.innerHTML;
              // reattach followup handlers for any replaced buttons
              if (window.attachFollowupHandlers) window.attachFollowupHandlers();
              if (window.applyPatientFilters) window.applyPatientFilters();
            }
          } catch (e) {
            console.warn('Unable to refresh patient list after check-in', e);
          }
        } catch (err) {
          console.error('Checkin error', err);
          alert('Network error');
        }
      });
    });
  }

  // === Refresh check-ins list ===
  async function refreshCheckinsList() {
    const checkinsList = document.querySelector('#checkins-list');
    if (!checkinsList) return;
    try {
      const res = await fetch(window.location.pathname + (window.location.search ? '&' : '?') + '_=' + nowTs(), {
        cache: 'no-store',
        credentials: 'same-origin'
      });
      const html = await res.text();
      const parser = new DOMParser();
      const doc = parser.parseFromString(html, 'text/html');
      const newCheckinsList = doc.querySelector('#checkins-list');
      if (newCheckinsList) {
        checkinsList.innerHTML = newCheckinsList.innerHTML;
      }
    } catch (err) {
      console.error('Failed to refresh check-ins list:', err);
    }
  }

  // === Bootstrap ===
  function bootstrap() {
    // Initialize from DOM/cached state then fetch fresh
    loadFollowups().catch(err => {
      console.error('Followups load failed', err);
      attachCheckinHandlers();
    });
  }

  // Kick off on DOMContentLoaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bootstrap);
  } else {
    bootstrap();
  }

  // Expose functions for debugging/testing if needed
  window.__followups = {
    loadFollowups,
    renderFollowupsFromState,
    removeFollowupFromState,
    getCache: loadFollowupsCache,
    clearCache: function () { localStorage.removeItem(LOCAL_CACHE_KEY); window.followups = []; renderFollowupsFromState(); }
  };
})();
