// Elementy UI
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const player = document.getElementById('player');
const lessonCtx = document.getElementById('lessonCtx');
const liveText = document.getElementById('liveText');

// Stan
let streamRef = null;
let fullRecorder = null;
let fullChunks = [];
let liveId = null;
let isRecording = false;
let pollTimer = null;
let startInterval = null; // timer startu segmentów
let activeSegmentRecorders = [];

// Konfiguracja
const SEGMENT_MS = 10000;   // długość jednego segmentu (ms)
const OVERLAP_MS = 500;    // nakładka (ms)
const STEP_MS = Math.max(200, SEGMENT_MS - OVERLAP_MS); // co ile startuje nowy segment

async function startRecording() {
  const lessonId = lessonCtx?.dataset?.lessonId;
  if (!lessonId) { alert('Brak lessonId'); return; }

  // Start sesji – backend
  const sRes = await fetch(`/api/lesson/${lessonId}/stream/start`, { method: 'POST' });
  const sData = await sRes.json();
  if (sData.error || !sData.live_id) { alert('Nie udało się rozpocząć sesji.'); return; }
  liveId = sData.live_id;

  // Media stream
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  streamRef = stream;

  const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : 'audio/webm';

  // Pełny zapis do odsłuchu
  fullChunks = [];
  fullRecorder = new MediaRecorder(stream, { mimeType: mime });
  fullRecorder.ondataavailable = (e) => { if (e.data && e.data.size > 0) fullChunks.push(e.data); };
  fullRecorder.onstop = () => {
    const blob = new Blob(fullChunks, { type: 'audio/webm' });
    const url = URL.createObjectURL(blob);
    player.src = url;
    player.style.display = 'block';
  };
  fullRecorder.start();

  isRecording = true;
  startBtn.disabled = true;
  stopBtn.disabled = false;

  // Segmenty z overlapem
  let idx = 0;
  const startNewSegment = () => {
    if (!isRecording) return;
    try {
      const rec = new MediaRecorder(stream, { mimeType: mime });
      let segChunks = [];
      const thisIdx = idx++;
      rec.ondataavailable = (e) => { if (e.data && e.data.size > 0) segChunks.push(e.data); };
      rec.onstop = async () => {
        const blob = new Blob(segChunks, { type: 'audio/webm' });
        const form = new FormData();
        const filename = `chunk_${Date.now()}_${thisIdx}.webm`;
        form.append('audio', blob, filename);
        form.append('live_id', String(liveId));
        form.append('idx', String(thisIdx));
        form.append('overlap_ms', String(OVERLAP_MS));
        try {
          await fetch(`/api/lesson/${lessonId}/stream/chunk`, { method: 'POST', body: form });
        } catch (err) {
          console.error('Błąd wysyłki fragmentu:', err);
        }
        activeSegmentRecorders = activeSegmentRecorders.filter(x => x !== rec);
      };
      rec.start();
      activeSegmentRecorders.push(rec);
      setTimeout(() => { try { rec.state === 'recording' && rec.stop(); } catch {} }, SEGMENT_MS);
    } catch (e) {
      console.error('Błąd MediaRecorder segmentu:', e);
    }
  };

  startNewSegment();
  startInterval = setInterval(startNewSegment, STEP_MS);

  // Polling transkryptu
  pollTimer = setInterval(async () => {
    if (!liveId) return;
    try {
      const r = await fetch(`/api/live/${liveId}/text`);
      const d = await r.json();
      if (!d.error && typeof d.text === 'string') {
        liveText.textContent = d.text;
      }
    } catch {}
  }, 1500);
}

async function stopRecording() {
  isRecording = false;
  if (startInterval) { clearInterval(startInterval); startInterval = null; }
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }

  activeSegmentRecorders.forEach(rec => { try { rec.state === 'recording' && rec.stop(); } catch {} });
  activeSegmentRecorders = [];

  if (fullRecorder && fullRecorder.state !== 'inactive') {
    try { fullRecorder.stop(); } catch {}
  }
  if (streamRef) {
    try { streamRef.getTracks().forEach(t => t.stop()); } catch {}
    streamRef = null;
  }

  startBtn.disabled = false;
  stopBtn.disabled = true;

  const lessonId = lessonCtx?.dataset?.lessonId;
  if (liveId && lessonId) {
    try {
      const res = await fetch(`/api/lesson/${lessonId}/stream/stop`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ live_id: liveId }) });
      await res.json().catch(() => ({}));
    } catch {}
    // Po domknięciu – wyślij pełny zapis jako pojedynczy plik audio do lekcji
    try {
      if (fullChunks && fullChunks.length > 0) {
        const blob = new Blob(fullChunks, { type: 'audio/webm' });
        const form = new FormData();
        form.append('audio', blob, `nagranie_${Date.now()}.webm`);
        await fetch(`/api/lesson/${lessonId}/record/upload`, { method: 'POST', body: form });
      }
    } catch {}
    // Przejdź do widoku lekcji (lista transkrypcji nie będzie pusta)
    window.location.href = `/lesson/${lessonId}`;
  }
}

startBtn?.addEventListener('click', startRecording);
stopBtn?.addEventListener('click', stopRecording);
