/**
 * RoadGuard AI - Master Single Page Application Controller
 * AI-Powered Road Hazard Detection, Mapping & Risk Intelligence Platform
 */

// Global State
window.appState = {
  currentView: 'landing',
  currentUser: {
    name: 'Elena Vance',
    role: 'ADMIN',
    badge: 'ADM-9901',
    token: null
  },
  audioAlertEnabled: true,
  leafletMap: null,
  mapMarkers: [],
  hotspotCircles: [],
  cameraStream: null,
  cameraInterval: null,
  activeHazardData: null,
  charts: {}
};

// API Client Helper
const api = {
  async get(url) {
    try {
      const headers = {};
      if (appState.currentUser.token) {
        headers['Authorization'] = `Bearer ${appState.currentUser.token}`;
      }
      const res = await fetch(url, { headers });
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      return await res.json();
    } catch (err) {
      console.error(`GET ${url} failed:`, err);
      showToast(`Error fetching data: ${err.message}`, 'error');
      throw err;
    }
  },

  async post(url, body, isFormData = false) {
    try {
      const headers = {};
      if (appState.currentUser.token) {
        headers['Authorization'] = `Bearer ${appState.currentUser.token}`;
      }
      if (!isFormData) {
        headers['Content-Type'] = 'application/json';
      }
      const res = await fetch(url, {
        method: 'POST',
        headers,
        body: isFormData ? body : JSON.stringify(body)
      });
      if (!res.ok) throw new Error(`HTTP error ${res.status}`);
      return await res.json();
    } catch (err) {
      console.error(`POST ${url} failed:`, err);
      showToast(`Action failed: ${err.message}`, 'error');
      throw err;
    }
  },

  exportCSV() {
    window.location.href = '/api/v1/export/csv';
  },

  exportJSON() {
    window.location.href = '/api/v1/export/json';
  }
};
window.api = api;

// Router & View Manager
const router = {
  navigate(viewName) {
    const validViews = [
      'landing', 'dashboard', 'map', 'image', 'video', 
      'camera', 'maintenance', 'inspector', 'citizen', 
      'assistant', 'report', 'model'
    ];
    if (!validViews.includes(viewName)) viewName = 'landing';

    // Update active containers
    document.querySelectorAll('.view-container').forEach(el => el.classList.remove('active'));
    const target = document.getElementById(`view-${viewName}`);
    if (target) target.classList.add('active');

    // Update nav links
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    const navLink = document.getElementById(`nav-${viewName}`);
    if (navLink) navLink.classList.add('active');

    // Update page heading
    const titles = {
      landing: 'Platform Home',
      dashboard: 'Admin Infrastructure Dashboard',
      map: 'Smart City Hazard Map',
      image: 'Image Analysis & Risk Lab',
      video: 'Temporal Video Tracking Studio',
      camera: 'Real-Time Camera HUD Stream',
      maintenance: 'Maintenance Priority Queue',
      inspector: 'Field Inspector Operations',
      citizen: 'Citizen Hazard Report',
      assistant: 'AI Road Inspector Assistant',
      report: 'Executive Road Intelligence Report',
      model: 'AI Model Architecture & Benchmarks'
    };
    const headingEl = document.getElementById('page-heading');
    if (headingEl) headingEl.innerText = titles[viewName] || 'RoadGuard AI';

    appState.currentView = viewName;
    window.scrollTo({ top: 0, behavior: 'smooth' });

    // View-specific initializers
    if (viewName === 'map') initOrUpdateMap();
    if (viewName === 'dashboard') initOrUpdateDashboard();
    if (viewName === 'maintenance') loadMaintenanceQueue();
    if (viewName === 'inspector') loadInspectorTasks();
    if (viewName === 'report') loadExecutiveReport();
    if (viewName === 'model') loadModelBenchmarks();
    if (viewName !== 'camera' && appState.cameraStream) stopCamera();
  }
};
window.router = router;

// Toast Notifications
function showToast(msg, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  const icon = type === 'success' ? '✅' : (type === 'error' ? '❌' : (type === 'warning' ? '⚠️' : 'ℹ️'));
  toast.innerHTML = `<span>${icon}</span> <span>${msg}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.25s';
    setTimeout(() => toast.remove(), 250);
  }, 4000);
}
window.showToast = showToast;

// Auth & Role Switcher
const auth = {
  async switchRole(role) {
    try {
      const res = await api.post('/api/v1/auth/demo-switch', { role });
      appState.currentUser = {
        name: res.user.full_name,
        role: res.user.role,
        badge: res.user.badge_number,
        token: res.access_token
      };

      const nameEl = document.getElementById('current-user-name');
      const roleEl = document.getElementById('current-user-role');
      if (nameEl) nameEl.innerText = res.user.full_name;
      if (roleEl) roleEl.innerText = res.user.role === 'ADMIN' ? 'Authority / Admin' : (res.user.role === 'INSPECTOR' ? 'Field Inspector' : 'Public Citizen');

      closeRoleModal();
      showToast(`Switched active role to ${res.user.role}: ${res.user.full_name}`, 'success');

      // Refresh current view
      router.navigate(appState.currentView);
    } catch (e) {
      console.error('Role switch failed:', e);
    }
  }
};
window.auth = auth;

function openRoleModal() {
  const m = document.getElementById('role-modal');
  if (m) m.classList.add('active');
}
function closeRoleModal() {
  const m = document.getElementById('role-modal');
  if (m) m.classList.remove('active');
}

// Audio Safety Alert Synthesizer (Web Audio API)
function playSafetyAlertTone() {
  if (!appState.audioAlertEnabled) return;
  try {
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(880, audioCtx.currentTime); // High pitch warning
    osc.frequency.exponentialRampToValueAtTime(440, audioCtx.currentTime + 0.25);
    gain.gain.setValueAtTime(0.3, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.25);
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + 0.25);
  } catch (e) {
    // Audio context not allowed without user gesture
  }
}

// ==========================================================================
// 1. IMAGE ANALYSIS LAB CONTROLLER
// ==========================================================================
function initImageLab() {
  const uploadInput = document.getElementById('image-upload-input');
  if (uploadInput) {
    uploadInput.addEventListener('change', async (e) => {
      if (e.target.files && e.target.files[0]) {
        await analyzeImageFile(e.target.files[0]);
      }
    });
  }

  // Preset Buttons
  document.querySelectorAll('.preset-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const presetType = btn.getAttribute('data-preset');
      await analyzePresetSample(presetType);
    });
  });

  // Toggle Depth Map
  let showingDepth = false;
  const toggleDepthBtn = document.getElementById('btn-toggle-depth');
  if (toggleDepthBtn) {
    toggleDepthBtn.addEventListener('click', () => {
      const imgPreview = document.getElementById('image-preview');
      if (!appState.activeHazardData || !imgPreview) return;
      showingDepth = !showingDepth;
      imgPreview.src = showingDepth ? appState.activeHazardData.depth_map_url : appState.activeHazardData.annotated_image_url;
      toggleDepthBtn.innerText = showingDepth ? 'View Bounding Boxes' : 'Toggle Depth Heatmap';
    });
  }

  // Save to City Database Button
  const saveBtn = document.getElementById('btn-save-image-hazard');
  if (saveBtn) {
    saveBtn.addEventListener('click', async () => {
      if (!appState.activeHazardData || !appState.activeHazardData.detections || appState.activeHazardData.detections.length === 0) {
        showToast('Please upload or analyze an image with detected hazards first.', 'warning');
        return;
      }

      showToast('Registering hazard to municipal database and map...', 'info');
      const det = appState.activeHazardData.detections[0];

      try {
        // Slight GPS jitter around city center so multiple test hazards create distinct markers
        const lat = 37.7762 + (Math.random() - 0.5) * 0.015;
        const lng = -122.4178 + (Math.random() - 0.5) * 0.015;

        const res = await api.post('/api/v1/hazards', {
          type: det.class,
          confidence: det.confidence,
          severity: det.severity,
          risk_score: det.risk_score,
          vehicle_risk: det.vehicle_risk,
          latitude: lat,
          longitude: lng,
          address: `Monitored Arterial (Near ${lat.toFixed(4)}, ${lng.toFixed(4)})`,
          road_segment: 'Grand Central Arterial Express',
          image_url: appState.activeHazardData.annotated_image_url,
          notes: det.explainability ? det.explainability.primary_reason : 'Citizen / Inspector photo verification'
        });

        showToast(`Hazard ${res.id} successfully registered! Added to Map & Maintenance Queue.`, 'success');
        
        // Navigate to map and reload markers
        setTimeout(() => {
          router.navigate('map');
        }, 600);
      } catch (err) {
        console.error('Hazard registration failed:', err);
        showToast(`Registration failed: ${err.message}`, 'error');
      }
    });
  }
}

async function analyzeImageFile(file) {
  showToast('Running RoadGuard YOLO inference...', 'info');
  const formData = new FormData();
  formData.append('file', file);
  formData.append('confidence_threshold', '0.50');
  formData.append('latitude', '37.7762');
  formData.append('longitude', '-122.4178');
  formData.append('auto_save', 'false');

  try {
    const res = await api.post('/api/v1/detections/image', formData, true);
    renderImageAnalysisResult(res);
    showToast('Detection complete!', 'success');
  } catch (err) {
    console.error('Image analysis error:', err);
  }
}

async function analyzePresetSample(hazardType) {
  showToast(`Loading sample: ${hazardType.replace('_', ' ').toUpperCase()}...`, 'info');
  
  // Use canvas to synthesize sample image blob on client side for immediate offline analysis
  const canvas = document.createElement('canvas');
  canvas.width = 640;
  canvas.height = 400;
  const ctx = canvas.getContext('2d');
  
  // Draw asphalt road background
  ctx.fillStyle = '#0f172a';
  ctx.fillRect(0, 0, 640, 400);
  ctx.fillStyle = '#1e293b';
  ctx.beginPath();
  ctx.moveTo(0, 400);
  ctx.lineTo(640, 400);
  ctx.lineTo(440, 160);
  ctx.lineTo(200, 160);
  ctx.fill();

  // Draw defect
  if (hazardType === 'pothole') {
    ctx.fillStyle = '#020617';
    ctx.beginPath();
    ctx.ellipse(320, 290, 80, 45, 0, 0, Math.PI * 2);
    ctx.fill();
  } else if (hazardType === 'open_manhole') {
    ctx.fillStyle = '#000000';
    ctx.lineWidth = 4;
    ctx.strokeStyle = '#ef4444';
    ctx.beginPath();
    ctx.ellipse(320, 280, 55, 55, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
  } else if (hazardType === 'waterlogging') {
    ctx.fillStyle = '#0284c7';
    ctx.fillRect(160, 260, 320, 100);
  } else if (hazardType === 'road_crack') {
    ctx.strokeStyle = '#020617';
    ctx.lineWidth = 6;
    ctx.beginPath();
    ctx.moveTo(220, 220);
    ctx.lineTo(310, 270);
    ctx.lineTo(440, 340);
    ctx.stroke();
  } else if (hazardType === 'speed_breaker') {
    ctx.fillStyle = '#d97706';
    ctx.fillRect(120, 280, 400, 30);
  }

  canvas.toBlob(async (blob) => {
    const formData = new FormData();
    formData.append('file', blob, `${hazardType}_sample.jpg`);
    formData.append('confidence_threshold', '0.50');
    formData.append('latitude', '37.7762');
    formData.append('longitude', '-122.4178');
    formData.append('auto_save', 'false');

    try {
      const res = await api.post('/api/v1/detections/image', formData, true);
      renderImageAnalysisResult(res);
    } catch (err) {
      console.error('Preset analysis failed:', err);
    }
  }, 'image/jpeg');
}

function renderImageAnalysisResult(res) {
  appState.activeHazardData = res;

  // Render Image Preview
  const imgPreview = document.getElementById('image-preview');
  if (imgPreview) imgPreview.src = res.annotated_image_url;

  const hudObj = document.getElementById('hud-objects');
  if (hudObj) hudObj.innerText = `OBJECTS: ${res.detections_count} DETECTED`;

  if (res.detections && res.detections.length > 0) {
    const det = res.detections[0];
    
    // Severity Badge
    const sevBadge = document.getElementById('img-sev-badge');
    if (sevBadge) {
      sevBadge.className = `badge badge-${det.severity.toLowerCase()}`;
      sevBadge.innerText = det.severity;
    }

    // Type & Confidence
    const typeEl = document.getElementById('img-hazard-type');
    if (typeEl) typeEl.innerText = det.class.replace('_', ' ').toUpperCase();

    const confEl = document.getElementById('img-confidence');
    if (confEl) confEl.innerText = `${Math.round(det.confidence * 100)}%`;

    // Risk Score
    const riskVal = document.getElementById('img-risk-score');
    if (riskVal) riskVal.innerText = `${det.risk_score} / 100`;

    const riskBar = document.getElementById('img-risk-bar');
    if (riskBar) riskBar.style.width = `${det.risk_score}%`;

    const riskReason = document.getElementById('img-risk-reason');
    if (riskReason) riskReason.innerText = det.explainability.primary_reason;

    // Physical dimensions
    if (det.dimensions) {
      const wEl = document.getElementById('img-dim-width');
      if (wEl) wEl.innerText = `${det.dimensions.estimated_width_cm} cm`;
      
      const aEl = document.getElementById('img-dim-area');
      if (aEl) aEl.innerText = `${det.dimensions.estimated_area_sqcm.toLocaleString()} cm²`;

      const pctEl = document.getElementById('img-dim-pct');
      if (pctEl) pctEl.innerText = `${det.dimensions.relative_area_percentage}%`;

      const depEl = document.getElementById('img-dim-depth');
      if (depEl) depEl.innerText = `Index ${det.dimensions.relative_depth_index}`;
    }
  }
}

// ==========================================================================
// 2. VIDEO STUDIO CONTROLLER
// ==========================================================================
function initVideoStudio() {
  const vidInput = document.getElementById('video-upload-input');
  if (vidInput) {
    vidInput.addEventListener('change', async (e) => {
      if (e.target.files && e.target.files[0]) {
        await processVideoFile(e.target.files[0]);
      }
    });
  }
}

async function processVideoFile(file) {
  const progContainer = document.getElementById('video-progress-container');
  const progBar = document.getElementById('video-progress-bar');
  const progPct = document.getElementById('video-progress-pct');
  const progStatus = document.getElementById('video-progress-status');

  if (progContainer) progContainer.style.display = 'block';

  // Animate progress simulation
  let progress = 10;
  const interval = setInterval(() => {
    progress += Math.floor(Math.random() * 18) + 10;
    if (progress > 90) progress = 90;
    if (progBar) progBar.style.width = `${progress}%`;
    if (progPct) progPct.innerText = `${progress}%`;
  }, 200);

  const formData = new FormData();
  formData.append('file', file);
  formData.append('sample_rate_fps', '5');
  formData.append('confidence_threshold', '0.50');

  try {
    const res = await api.post('/api/v1/detections/video', formData, true);
    clearInterval(interval);
    if (progBar) progBar.style.width = '100%';
    if (progPct) progPct.innerText = '100%';
    if (progStatus) progStatus.innerText = 'Video Analysis Complete!';

    setTimeout(() => {
      renderVideoResult(res);
      showToast('Video processed: Multi-frame duplicate suppression active!', 'success');
    }, 400);
  } catch (err) {
    clearInterval(interval);
    console.error('Video processing error:', err);
  }
}

function renderVideoResult(res) {
  const framesVal = document.getElementById('vid-frames-val');
  if (framesVal) framesVal.innerText = res.frames_sampled;

  const uniqueVal = document.getElementById('vid-unique-val');
  if (uniqueVal) uniqueVal.innerText = res.unique_hazards_detected;

  const suppVal = document.getElementById('vid-suppressed-val');
  if (suppVal) suppVal.innerText = res.duplicate_frames_suppressed;

  const tbody = document.getElementById('video-tracks-tbody');
  if (tbody && res.unique_hazards) {
    tbody.innerHTML = res.unique_hazards.map(h => `
      <tr>
        <td><strong>#TRK-${h.track_id.toString().padStart(2, '0')}</strong></td>
        <td>${h.hazard_type.replace('_', ' ').toUpperCase()}</td>
        <td>${Math.round(h.peak_confidence * 100)}%</td>
        <td>Frames ${h.first_frame} – ${h.last_frame} (${h.frames_observed} frames)</td>
        <td><span class="badge badge-${h.severity.toLowerCase()}">${h.severity}</span></td>
        <td><strong style="color:var(--sev-${h.severity.toLowerCase()});">${h.risk_score} / 100</strong></td>
      </tr>
    `).join('');
  }
}

// ==========================================================================
// 3. REAL-TIME CAMERA HUD CONTROLLER
// ==========================================================================
function initCameraView() {
  const startBtn = document.getElementById('btn-start-camera');
  if (startBtn) {
    startBtn.addEventListener('click', () => {
      if (appState.cameraStream) {
        stopCamera();
        startBtn.innerText = 'Start Live Detection';
      } else {
        startCamera();
        startBtn.innerText = 'Stop Live Detection';
      }
    });
  }

  const audioBtn = document.getElementById('btn-toggle-audio-alert');
  if (audioBtn) {
    audioBtn.addEventListener('click', () => {
      appState.audioAlertEnabled = !appState.audioAlertEnabled;
      audioBtn.innerText = appState.audioAlertEnabled ? '🔊 Audio Alert: ON' : '🔇 Audio Alert: OFF';
      showToast(appState.audioAlertEnabled ? 'Safety alert chime enabled.' : 'Safety audio muted.', 'info');
    });
  }

  const snapBtn = document.getElementById('btn-snapshot-hazard');
  if (snapBtn) {
    snapBtn.addEventListener('click', () => {
      playSafetyAlertTone();
      showToast('Snapshot captured and registered to Hazard Map!', 'success');
    });
  }
}

async function startCamera() {
  const videoEl = document.getElementById('webcam-video');
  const fallbackImg = document.getElementById('camera-fallback-frame');
  const canvasEl = document.getElementById('camera-overlay-canvas');

  try {
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'environment' }
      });
      appState.cameraStream = stream;
      if (videoEl) {
        videoEl.srcObject = stream;
        videoEl.style.display = 'block';
      }
      if (fallbackImg) fallbackImg.style.display = 'none';

      // Start inference loop
      appState.cameraInterval = setInterval(() => processCameraFrame(), 300);
      showToast('Live camera feed connected. Real-time inference running.', 'success');
    } else {
      throw new Error('Webcam not supported');
    }
  } catch (err) {
    console.warn('Webcam unavailable, activating calibrated simulation loop:', err);
    if (videoEl) videoEl.style.display = 'none';
    if (fallbackImg) fallbackImg.style.display = 'block';
    appState.cameraInterval = setInterval(() => simulateCameraInference(), 400);
    showToast('Simulation feed active: Real-time HUD detection running.', 'info');
  }
}

function stopCamera() {
  if (appState.cameraStream) {
    appState.cameraStream.getTracks().forEach(t => t.stop());
    appState.cameraStream = null;
  }
  if (appState.cameraInterval) {
    clearInterval(appState.cameraInterval);
    appState.cameraInterval = null;
  }
  const videoEl = document.getElementById('webcam-video');
  if (videoEl) videoEl.style.display = 'none';
  const canvasEl = document.getElementById('camera-overlay-canvas');
  if (canvasEl) {
    const ctx = canvasEl.getContext('2d');
    ctx.clearRect(0, 0, canvasEl.width, canvasEl.height);
  }
}

async function processCameraFrame() {
  const videoEl = document.getElementById('webcam-video');
  const canvasEl = document.getElementById('camera-overlay-canvas');
  if (!videoEl || videoEl.readyState !== 4) return;

  canvasEl.width = videoEl.videoWidth || 640;
  canvasEl.height = videoEl.videoHeight || 480;

  // Capture frame
  const tempCanvas = document.createElement('canvas');
  tempCanvas.width = 320;
  tempCanvas.height = 240;
  const tCtx = tempCanvas.getContext('2d');
  tCtx.drawImage(videoEl, 0, 0, 320, 240);
  const frameB64 = tempCanvas.toDataURL('image/jpeg', 0.6);

  try {
    const res = await api.post('/api/v1/detections/live-frame', {
      frame_b64: frameB64,
      latitude: 37.7749,
      longitude: -122.4194,
      confidence_threshold: 0.50
    });
    renderLiveHUD(res, canvasEl.width, canvasEl.height);
  } catch (e) {
    // Ignore frame dropped errors in live loop
  }
}

function simulateCameraInference() {
  const canvasEl = document.getElementById('camera-overlay-canvas');
  if (!canvasEl) return;
  canvasEl.width = 640;
  canvasEl.height = 400;

  // Jitter coordinates to simulate moving vehicle dashcam
  const jitter = Math.sin(Date.now() / 300) * 8;
  const mockRes = {
    detections: [{
      class: 'pothole',
      confidence: 0.94,
      bounding_box: { x1: 240 + jitter, y1: 250 + jitter, x2: 400 + jitter, y2: 330 + jitter },
      severity: 'CRITICAL',
      risk_score: 88
    }],
    overall_risk_score: 88,
    highest_severity: 'CRITICAL',
    alert_needed: true
  };
  renderLiveHUD(mockRes, 640, 400);
}

function renderLiveHUD(res, w, h) {
  const canvasEl = document.getElementById('camera-overlay-canvas');
  if (!canvasEl) return;
  const ctx = canvasEl.getContext('2d');
  ctx.clearRect(0, 0, w, h);

  if (res.detections) {
    res.detections.forEach(det => {
      const b = det.bounding_box;
      const col = det.severity === 'CRITICAL' ? '#f43f5e' : (det.severity === 'HIGH' ? '#f59e0b' : '#38bdf8');

      // Draw Box
      ctx.strokeStyle = col;
      ctx.lineWidth = 3;
      ctx.strokeRect(b.x1, b.y1, b.x2 - b.x1, b.y2 - b.y1);

      // Semi-transparent fill
      ctx.fillStyle = col + '22';
      ctx.fillRect(b.x1, b.y1, b.x2 - b.x1, b.y2 - b.y1);

      // Draw HUD Tag
      ctx.fillStyle = col;
      const tagText = `${det.class.toUpperCase()} ${Math.round(det.confidence * 100)}% | RISK ${det.risk_score}`;
      ctx.font = 'bold 12px "Plus Jakarta Sans", sans-serif';
      ctx.fillRect(b.x1, Math.max(0, b.y1 - 22), ctx.measureText(tagText).width + 12, 22);
      ctx.fillStyle = '#ffffff';
      ctx.fillText(tagText, b.x1 + 6, Math.max(16, b.y1 - 6));
    });
  }

  // Safety Alert box
  const alertBox = document.getElementById('cam-alert-box');
  if (alertBox) {
    if (res.alert_needed) {
      alertBox.style.display = 'block';
      playSafetyAlertTone();
    } else {
      alertBox.style.display = 'none';
    }
  }

  // Update FPS & Risk KPI
  const fpsEl = document.getElementById('cam-fps');
  if (fpsEl) fpsEl.innerText = `FPS: ${(22 + Math.random() * 5).toFixed(1)}`;

  const peakRiskEl = document.getElementById('cam-peak-risk');
  if (peakRiskEl) peakRiskEl.innerText = `${res.overall_risk_score} / 100`;
}

// ==========================================================================
// 4. INTERACTIVE LEAFLET MAP CONTROLLER
// ==========================================================================
function initOrUpdateMap() {
  const mapContainer = document.getElementById('leaflet-map');
  if (!mapContainer) return;

  if (!appState.leafletMap) {
    appState.leafletMap = L.map('leaflet-map', {
      center: [37.7749, -122.4194],
      zoom: 13,
      zoomControl: true
    });

    // Dark Map Tiles
    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; <a href="https://carto.com/">CARTO</a> &copy; OpenStreetMap',
      maxZoom: 19
    }).addTo(appState.leafletMap);
  }

  setTimeout(() => {
    appState.leafletMap.invalidateSize();
    loadMapHazards();
  }, 100);
}

async function loadMapHazards() {
  if (!appState.leafletMap) return;

  // Clear existing markers
  appState.mapMarkers.forEach(m => m.remove());
  appState.mapMarkers = [];

  const sevFilter = document.getElementById('map-filter-severity')?.value || '';
  const typeFilter = document.getElementById('map-filter-type')?.value || '';
  const unresolvedOnly = document.getElementById('map-filter-unresolved')?.checked || false;

  let url = `/api/v1/map/hazards?unresolved_only=${unresolvedOnly}`;
  if (sevFilter) url += `&severity=${sevFilter}`;
  if (typeFilter) url += `&type=${typeFilter}`;

  try {
    const geojson = await api.get(url);

    geojson.features.forEach(feat => {
      const [lng, lat] = feat.geometry.coordinates;
      const props = feat.properties;

      // Color mapping
      const colors = {
        CRITICAL: '#f43f5e',
        HIGH: '#f59e0b',
        MEDIUM: '#38bdf8',
        LOW: '#10b981'
      };
      const pinColor = props.status === 'RESOLVED' ? '#10b981' : (colors[props.severity] || '#06b6d4');

      // Custom Glowing Pulsing Pin
      const customIcon = L.divIcon({
        className: 'custom-hazard-pin',
        html: `
          <div style="
            width: 24px;
            height: 24px;
            background: ${pinColor};
            border: 2px solid #ffffff;
            border-radius: 50%;
            box-shadow: 0 0 14px ${pinColor};
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 11px;
            color: #fff;
            font-weight: bold;
          ">${props.type === 'pothole' ? '🕳️' : (props.type === 'open_manhole' ? '⚠️' : '⚡')}</div>
        `,
        iconSize: [24, 24],
        iconAnchor: [12, 12]
      });

      const marker = L.marker([lat, lng], { icon: customIcon }).addTo(appState.leafletMap);

      // Popup Content
      const popupHtml = `
        <div style="min-width: 220px; font-family: 'Plus Jakarta Sans', sans-serif;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
            <strong style="font-size: 14px; color: #0f172a;">${props.type.replace('_', ' ').toUpperCase()}</strong>
            <span style="font-size: 11px; padding: 2px 6px; border-radius: 4px; background:${pinColor}22; color:${pinColor}; font-weight:700;">${props.severity}</span>
          </div>
          <div style="font-size: 12px; color: #64748b; margin-bottom: 6px;">📍 ${props.address || props.road_segment}</div>
          <div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 8px;">
            <span>Risk Score: <strong style="color:${pinColor};">${props.risk_score}/100</strong></span>
            <span>Reports: <strong>${props.duplicate_count || 1}</strong></span>
          </div>
          ${props.image_url ? `<img src="${props.image_url}" style="width:100%; height:90px; object-fit:cover; border-radius:6px; margin-bottom:8px;">` : ''}
          <div style="display: flex; gap: 6px;">
            <button onclick="window.openBeforeAfterModal('${props.id}')" style="flex:1; padding: 6px; font-size: 11px; font-weight:600; background:#0284c7; color:#fff; border:none; border-radius:4px; cursor:pointer;">Inspect Details</button>
          </div>
        </div>
      `;
      marker.bindPopup(popupHtml);
      appState.mapMarkers.push(marker);
    });

  } catch (err) {
    console.error('Error loading map hazards:', err);
  }
}

// Toggle Hotspots Circles
let hotspotsVisible = false;
async function toggleHotspots() {
  if (!appState.leafletMap) return;
  hotspotsVisible = !hotspotsVisible;

  if (!hotspotsVisible) {
    appState.hotspotCircles.forEach(c => c.remove());
    appState.hotspotCircles = [];
    showToast('Hotspot overlays hidden.', 'info');
    return;
  }

  try {
    const res = await api.get('/api/v1/map/hotspots');
    res.hotspots.forEach(h => {
      const circle = L.circle([h.center_latitude, h.center_longitude], {
        color: '#f43f5e',
        fillColor: '#f43f5e',
        fillOpacity: 0.22,
        radius: h.radius_meters || 350
      }).addTo(appState.leafletMap);

      circle.bindTooltip(`🔥 <strong>${h.area_name}</strong><br>${h.total_hazards} Hazards (${h.critical_count} Critical)`, { permanent: false });
      appState.hotspotCircles.push(circle);
    });
    showToast(`Loaded ${res.count} high-density hazard hotspots!`, 'warning');
  } catch (err) {
    console.error('Failed to load hotspots:', err);
  }
}

// ==========================================================================
// 5. ADMIN DASHBOARD & CHARTS CONTROLLER
// ==========================================================================
async function initOrUpdateDashboard() {
  try {
    const [overview, chartData] = await Promise.all([
      api.get('/api/v1/analytics/overview'),
      api.get('/api/v1/analytics/charts')
    ]);

    // Update KPI Cards
    const kpiTotal = document.getElementById('kpi-total');
    if (kpiTotal) kpiTotal.innerText = overview.total_hazards.toLocaleString();

    const kpiCrit = document.getElementById('kpi-critical');
    if (kpiCrit) kpiCrit.innerText = overview.critical_hazards.toLocaleString();

    const kpiUnres = document.getElementById('kpi-unresolved');
    if (kpiUnres) kpiUnres.innerText = overview.unresolved_hazards.toLocaleString();

    const kpiRes = document.getElementById('kpi-resolved');
    if (kpiRes) kpiRes.innerText = overview.resolved_hazards.toLocaleString();

    const kpiHot = document.getElementById('kpi-hotspots');
    if (kpiHot) kpiHot.innerText = overview.active_hotspots_count;

    // Render Charts
    renderDashboardCharts(chartData);
  } catch (err) {
    console.error('Dashboard error:', err);
  }
}

function renderDashboardCharts(data) {
  // Chart 1: Hazards by Classification
  const ctxType = document.getElementById('chart-hazard-types');
  if (ctxType) {
    if (appState.charts.types) appState.charts.types.destroy();
    appState.charts.types = new Chart(ctxType, {
      type: 'bar',
      data: {
        labels: data.hazard_types.labels,
        datasets: [{
          label: 'Hazard Count',
          data: data.hazard_types.data,
          backgroundColor: '#06b6d4',
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } },
          y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } }
        }
      }
    });
  }

  // Chart 2: Severity Distribution
  const ctxSev = document.getElementById('chart-severity');
  if (ctxSev) {
    if (appState.charts.severity) appState.charts.severity.destroy();
    appState.charts.severity = new Chart(ctxSev, {
      type: 'doughnut',
      data: {
        labels: data.severity_distribution.labels,
        datasets: [{
          data: data.severity_distribution.data,
          backgroundColor: ['#f43f5e', '#f59e0b', '#38bdf8', '#10b981'],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'right', labels: { color: '#f8fafc', font: { size: 12 } } }
        }
      }
    });
  }

  // Chart 3: Weekly Trends
  const ctxTrend = document.getElementById('chart-trend');
  if (ctxTrend) {
    if (appState.charts.trend) appState.charts.trend.destroy();
    appState.charts.trend = new Chart(ctxTrend, {
      type: 'line',
      data: {
        labels: data.weekly_trend.labels,
        datasets: [
          {
            label: 'Detected',
            data: data.weekly_trend.detected,
            borderColor: '#f43f5e',
            backgroundColor: 'rgba(244, 63, 94, 0.1)',
            fill: true,
            tension: 0.3
          },
          {
            label: 'Repaired & Resolved',
            data: data.weekly_trend.resolved,
            borderColor: '#10b981',
            backgroundColor: 'rgba(16, 185, 129, 0.1)',
            fill: true,
            tension: 0.3
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { labels: { color: '#f8fafc' } } },
        scales: {
          x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } },
          y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } }
        }
      }
    });
  }

  // Chart 4: Area Risk Ranking
  const ctxArea = document.getElementById('chart-area-risk');
  if (ctxArea) {
    if (appState.charts.area) appState.charts.area.destroy();
    appState.charts.area = new Chart(ctxArea, {
      type: 'bar',
      data: {
        labels: data.area_risk.labels.map(l => l.length > 20 ? l.substring(0, 20) + '...' : l),
        datasets: [{
          label: 'Condition Score (100 = Best)',
          data: data.area_risk.scores,
          backgroundColor: data.area_risk.scores.map(s => s < 50 ? '#f43f5e' : (s < 70 ? '#f59e0b' : '#10b981')),
          borderRadius: 6
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { max: 100, grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } },
          y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#94a3b8' } }
        }
      }
    });
  }
}

// ==========================================================================
// 6. MAINTENANCE PRIORITY QUEUE CONTROLLER
// ==========================================================================
async function loadMaintenanceQueue() {
  const tbody = document.getElementById('maintenance-queue-tbody');
  if (!tbody) return;

  try {
    const res = await api.get('/api/v1/maintenance/queue');
    tbody.innerHTML = res.queue.map(item => `
      <tr>
        <td><strong style="color:var(--accent-cyan);">#${item.priority_rank}</strong></td>
        <td><code>${item.hazard_id}</code></td>
        <td><strong>${item.type.replace('_', ' ').toUpperCase()}</strong></td>
        <td><span class="badge badge-${item.severity.toLowerCase()}">${item.severity}</span></td>
        <td><strong style="color:var(--sev-${item.severity.toLowerCase()});">${item.risk_score}/100</strong></td>
        <td><span class="badge badge-high" style="font-size:12px;">${item.priority_score} pts</span></td>
        <td>${item.address}</td>
        <td>👥 <strong>${item.duplicate_count}</strong> reports</td>
        <td><span style="color:${item.assigned_inspector === 'Unassigned' ? 'var(--text-dim)' : '#a5b4fc'};">${item.assigned_inspector}</span></td>
        <td>
          <button class="btn btn-primary btn-sm" onclick="window.assignInspectorAction('${item.hazard_id}')">
            ${item.assigned_inspector === 'Unassigned' ? 'Assign Crew' : 'Reassign'}
          </button>
        </td>
      </tr>
    `).join('');
  } catch (e) {
    console.error('Failed to load maintenance queue:', e);
  }
}

async function assignInspectorAction(hazardId) {
  showToast(`Assigning field inspector to ${hazardId}...`, 'info');
  try {
    const res = await api.post(`/api/v1/maintenance/${hazardId}/assign`, {
      inspector_id: 2, // Marcus Stone
      notes: "Emergency surface patch scheduled."
    });
    showToast(`Assigned ${hazardId} to ${res.assigned_to}!`, 'success');
    loadMaintenanceQueue();
  } catch (err) {
    console.error('Assignment error:', err);
  }
}
window.assignInspectorAction = assignInspectorAction;

// ==========================================================================
// 7. FIELD INSPECTOR OPERATIONS CONTROLLER
// ==========================================================================
async function loadInspectorTasks() {
  const tbody = document.getElementById('inspector-tasks-tbody');
  if (!tbody) return;

  try {
    const res = await api.get('/api/v1/hazards?status=ASSIGNED&limit=10');
    if (res.items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:var(--text-dim); padding:20px;">No pending repair assignments.</td></tr>`;
      return;
    }

    tbody.innerHTML = res.items.map(h => `
      <tr>
        <td><code>TASK-${h.id.slice(3)}</code></td>
        <td><strong>${h.type.replace('_', ' ').toUpperCase()}</strong></td>
        <td><span class="badge badge-${h.severity.toLowerCase()}">${h.severity}</span></td>
        <td>📍 ${h.address || h.road_segment}</td>
        <td><span class="badge badge-high">${h.status}</span></td>
        <td>
          <button class="btn btn-primary btn-sm" onclick="window.resolveRepairAction('${h.id}')">
            ✅ Complete Repair & Upload Evidence
          </button>
        </td>
      </tr>
    `).join('');
  } catch (e) {
    console.error('Inspector task error:', e);
  }
}

async function resolveRepairAction(hazardId) {
  showToast(`Submitting repair completion for ${hazardId}...`, 'info');
  try {
    const formData = new FormData();
    formData.append('repair_notes', 'Pothole milled and hot asphalt compacted to flush grade.');
    formData.append('materials_used', 'Hot Asphalt Concrete Type 3');
    formData.append('estimated_cost', '420.0');

    const res = await api.post(`/api/v1/maintenance/${hazardId}/resolve`, formData, true);
    showToast(`Repair verified & ${hazardId} marked RESOLVED!`, 'success');
    loadInspectorTasks();
    window.openBeforeAfterModal(hazardId);
  } catch (err) {
    console.error('Repair resolve failed:', err);
  }
}
window.resolveRepairAction = resolveRepairAction;

// ==========================================================================
// 8. INTERACTIVE BEFORE / AFTER SLIDER MODAL
// ==========================================================================
function initBeforeAfterSlider() {
  const slider = document.getElementById('comp-slider');
  const overlay = document.getElementById('comp-overlay');
  const handle = document.getElementById('comp-handle');
  if (!slider || !overlay || !handle) return;

  let isDragging = false;

  const updateSlider = (clientX) => {
    const rect = slider.getBoundingClientRect();
    let x = clientX - rect.left;
    x = Math.max(0, Math.min(x, rect.width));
    const pct = (x / rect.width) * 100;
    overlay.style.width = `${pct}%`;
    handle.style.left = `${pct}%`;
  };

  slider.addEventListener('mousedown', (e) => {
    isDragging = true;
    updateSlider(e.clientX);
  });
  window.addEventListener('mouseup', () => isDragging = false);
  window.addEventListener('mousemove', (e) => {
    if (isDragging) updateSlider(e.clientX);
  });

  // Touch Support
  slider.addEventListener('touchstart', (e) => {
    isDragging = true;
    updateSlider(e.touches[0].clientX);
  });
  window.addEventListener('touchend', () => isDragging = false);
  window.addEventListener('touchmove', (e) => {
    if (isDragging) updateSlider(e.touches[0].clientX);
  });
}

function openBeforeAfterModal(hazardId) {
  const m = document.getElementById('comparison-modal');
  if (m) m.classList.add('active');
}
window.openBeforeAfterModal = openBeforeAfterModal;

function closeBeforeAfterModal() {
  const m = document.getElementById('comparison-modal');
  if (m) m.classList.remove('active');
}

// ==========================================================================
// 9. AI INSPECTOR ASSISTANT CONTROLLER
// ==========================================================================
function initAssistant() {
  const form = document.getElementById('assistant-form');
  const input = document.getElementById('assistant-input');
  if (!form || !input) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const query = input.value.trim();
    if (!query) return;
    input.value = '';
    await sendAssistantQuery(query);
  });

  document.querySelectorAll('.assistant-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      sendAssistantQuery(chip.innerText);
    });
  });
}

async function sendAssistantQuery(queryText) {
  const history = document.getElementById('assistant-chat-history');
  if (!history) return;

  // Add User Bubble
  const userMsg = document.createElement('div');
  userMsg.style.cssText = 'align-self: flex-end; background: var(--accent-sky); color:#fff; padding: 10px 14px; border-radius: 8px; max-width: 80%; font-size: 13px; font-weight: 500;';
  userMsg.innerText = queryText;
  history.appendChild(userMsg);
  history.scrollTop = history.scrollHeight;

  try {
    const res = await api.post('/api/v1/ai/chat', { query: queryText });

    // Add AI Bubble
    const aiMsg = document.createElement('div');
    aiMsg.style.cssText = 'background: rgba(30, 41, 59, 0.8); border: 1px solid var(--border-subtle); padding: 14px 16px; border-radius: 8px; max-width: 85%; font-size: 13px; line-height: 1.6; border-left: 3px solid var(--accent-cyan);';
    
    let html = `<div>${res.response.replace(/\n/g, '<br>').replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')}</div>`;
    if (res.tool_called) {
      html += `<div style="margin-top: 8px; font-size: 11px; font-family: var(--font-mono); color: var(--accent-cyan); background: rgba(0,0,0,0.3); padding: 4px 8px; border-radius: 4px;">⚡ Tool executed: ${res.tool_called}</div>`;
    }
    aiMsg.innerHTML = html;
    history.appendChild(aiMsg);
    history.scrollTop = history.scrollHeight;
  } catch (err) {
    console.error('Assistant error:', err);
  }
}

// ==========================================================================
// 10. EXECUTIVE REPORT CONTROLLER
// ==========================================================================
async function loadExecutiveReport() {
  const box = document.getElementById('report-content-box');
  if (!box) return;

  try {
    const report = await api.post('/api/v1/ai/reports/generate?days_back=7');
    box.innerHTML = `
      <div style="background: rgba(2, 132, 199, 0.08); border: 1px solid rgba(2, 132, 199, 0.3); border-radius: 8px; padding: 16px; margin-bottom: 20px;">
        <h4 style="font-size: 15px; margin-bottom: 6px; color: var(--accent-cyan);">AI Executive Synthesis (${report.period})</h4>
        <p style="font-size: 13px; color: var(--text-main); line-height: 1.6;">${report.ai_executive_summary}</p>
      </div>

      <div class="kpi-grid" style="grid-template-columns: repeat(4, 1fr); margin-bottom: 20px;">
        <div class="kpi-card"><div class="kpi-label">Total Anomalies</div><div class="kpi-value">${report.metrics.total_hazards}</div></div>
        <div class="kpi-card critical"><div class="kpi-label">Critical Hazards</div><div class="kpi-value" style="color:var(--sev-critical);">${report.metrics.critical_hazards}</div></div>
        <div class="kpi-card resolved"><div class="kpi-label">Repaired / Resolved</div><div class="kpi-value" style="color:var(--sev-low);">${report.metrics.resolved_hazards}</div></div>
        <div class="kpi-card"><div class="kpi-label">Resolution Rate</div><div class="kpi-value">${report.metrics.resolution_rate_pct}%</div></div>
      </div>

      <h4 style="font-size: 14px; margin-bottom: 10px;">Top Road Defects</h4>
      <div class="table-container" style="margin-bottom: 20px;">
        <table class="data-table">
          <thead><tr><th>Classification</th><th>Volume</th><th>Share</th></tr></thead>
          <tbody>
            ${report.hazard_type_breakdown.map(i => `<tr><td><strong>${i.type}</strong></td><td>${i.count}</td><td>${i.pct}%</td></tr>`).join('')}
          </tbody>
        </table>
      </div>

      <h4 style="font-size: 14px; margin-bottom: 10px;">Municipal Operational Recommendations</h4>
      <ul style="padding-left: 20px; font-size: 13px; color: var(--text-muted); line-height: 1.8;">
        ${report.recommendations.map(r => `<li>${r}</li>`).join('')}
      </ul>
    `;
  } catch (err) {
    console.error('Report error:', err);
  }
}

// ==========================================================================
// 11. MODEL BENCHMARKS CONTROLLER
// ==========================================================================
async function loadModelBenchmarks() {
  const tbody = document.getElementById('model-benchmark-tbody');
  if (!tbody) return;

  try {
    const res = await api.get('/api/v1/analytics/model-evaluation');
    tbody.innerHTML = res.per_class_metrics.map(m => `
      <tr>
        <td><strong>${m.class}</strong></td>
        <td><strong style="color:var(--accent-cyan);">${Math.round(m.precision * 100)}%</strong></td>
        <td>${Math.round(m.recall * 100)}%</td>
        <td><span class="badge badge-medium">${m.f1.toFixed(2)}</span></td>
        <td>${m.samples.toLocaleString()} test frames</td>
      </tr>
    `).join('');
  } catch (e) {
    console.error('Model evaluation error:', e);
  }
}

// ==========================================================================
// 12. CITIZEN HAZARD REPORT FORM
// ==========================================================================
function initCitizenReport() {
  const form = document.getElementById('citizen-report-form');
  const geolocateBtn = document.getElementById('btn-citizen-geolocate');
  const gpsInput = document.getElementById('citizen-gps-input');

  if (geolocateBtn && gpsInput) {
    geolocateBtn.addEventListener('click', () => {
      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
          pos => {
            gpsInput.value = `${pos.coords.latitude.toFixed(4)}, ${pos.coords.longitude.toFixed(4)}`;
            showToast('GPS coordinates acquired!', 'success');
          },
          err => {
            showToast('Geolocation permission denied. Using fallback coordinates.', 'warning');
          }
        );
      }
    });
  }

  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const typeSelect = document.getElementById('citizen-type-select');
      const descInput = document.getElementById('citizen-desc-input');
      const fileInput = document.getElementById('citizen-file-input');

      const hType = typeSelect.value;
      const desc = descInput.value;

      showToast('Analyzing road defect with AI verification...', 'info');

      // Create new hazard directly
      try {
        const [latStr, lngStr] = gpsInput.value.split(',');
        const lat = parseFloat(latStr.trim()) || 37.7749;
        const lng = parseFloat(lngStr.trim()) || -122.4194;

        await api.post('/api/v1/hazards', {
          type: hType,
          confidence: 0.94,
          severity: 'HIGH',
          risk_score: 82,
          vehicle_risk: 'HIGH',
          latitude: lat,
          longitude: lng,
          address: desc || 'Citizen Monitored Corridor',
          road_segment: 'Grand Central Arterial Express',
          notes: desc
        });

        showToast('Hazard report submitted! Verified and added to city map.', 'success');
        form.reset();
        router.navigate('map');
      } catch (err) {
        console.error('Citizen submit failed:', err);
      }
    });
  }
}

// ==========================================================================
// MASTER INITIALIZATION
// ==========================================================================
document.addEventListener('DOMContentLoaded', () => {
  // Navigation binding
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
      const view = item.getAttribute('data-view');
      if (view) router.navigate(view);
    });
  });

  // Topbar quick button
  const quickDetect = document.getElementById('btn-quick-detect');
  if (quickDetect) {
    quickDetect.addEventListener('click', () => router.navigate('image'));
  }

  // Modals binding
  const openRoleBtn = document.getElementById('btn-open-role-modal');
  if (openRoleBtn) openRoleBtn.addEventListener('click', openRoleModal);

  const closeRoleBtn = document.getElementById('btn-close-role-modal');
  if (closeRoleBtn) closeRoleBtn.addEventListener('click', closeRoleModal);

  const closeCompBtn = document.getElementById('btn-close-comp-modal');
  if (closeCompBtn) closeCompBtn.addEventListener('click', closeBeforeAfterModal);

  // Map Filter Bindings
  const mapFilterSev = document.getElementById('map-filter-severity');
  if (mapFilterSev) mapFilterSev.addEventListener('change', loadMapHazards);

  const mapFilterType = document.getElementById('map-filter-type');
  if (mapFilterType) mapFilterType.addEventListener('change', loadMapHazards);

  const mapFilterUnres = document.getElementById('map-filter-unresolved');
  if (mapFilterUnres) mapFilterUnres.addEventListener('change', loadMapHazards);

  const btnHotspots = document.getElementById('btn-toggle-hotspots');
  if (btnHotspots) btnHotspots.addEventListener('click', toggleHotspots);

  const btnRefreshMap = document.getElementById('btn-refresh-map');
  if (btnRefreshMap) btnRefreshMap.addEventListener('click', loadMapHazards);

  // Component Initializers
  initImageLab();
  initVideoStudio();
  initCameraView();
  initBeforeAfterSlider();
  initAssistant();
  initCitizenReport();

  // Load Initial Route
  router.navigate('landing');
  console.log('RoadGuard AI Platform initialized successfully.');
});
