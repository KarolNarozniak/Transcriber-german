let segmentRecorder;
let fullRecorder;
let fullChunks = [];
let isRecording = false;
let liveId = null;
let pollTimer = null;
let streamRef = null;

const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const uploadBtn = document.getElementById('uploadBtn');
const player = document.getElementById('player');

startBtn.addEventListener('click', async () => {
  const lessonCtx = document.getElementById('lessonCtx');
  const lessonId = lessonCtx?.dataset?.lessonId;
  if (!lessonId) { alert('Brak lessonId'); return; }

  // utwórz sesję live
  const sRes = await fetch(`/api/lesson/${lessonId}/stream/start`, { method: 'POST' });
  const sData = await sRes.json();
  if (sData.error || !sData.live_id) { alert('Nie udało się rozpocząć sesji.'); return; }
  liveId = sData.live_id;

  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  streamRef = stream;

  const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus' : 'audio/webm';

  // pełny zapis w tle
  fullChunks = [];
  fullRecorder = new MediaRecorder(stream, { mimeType: mime });
  fullRecorder.ondataavailable = (e) => { if (e.data && e.data.size > 0) fullChunks.push(e.data); };
  fullRecorder.onstop = () => {
    const blob = new Blob(fullChunks, { type: 'audio/webm' });
    const url = URL.createObjectURL(blob);
    player.src = url;
    player.style.display = 'block';
    uploadBtn.disabled = false;
  };
  fullRecorder.start();

  isRecording = true;
  startBtn.disabled = true;
  stopBtn.disabled = false;

  let idx = 0;
  const segmentMs = 10000;

  const recordSegment = () => {
    if (!isRecording) return;
    let segChunks = [];
    segmentRecorder = new MediaRecorder(stream, { mimeType: mime });
    segmentRecorder.ondataavailable = (e) => { if (e.data && e.data.size > 0) segChunks.push(e.data); };
    segmentRecorder.onstop = async () => {
      const blob = new Blob(segChunks, { type: 'audio/webm' });
      const form = new FormData();
      const filename = `chunk_${Date.now()}.webm`;
      form.append('audio', blob, filename);
      form.append('live_id', String(liveId));
      form.append('idx', String(idx++));
      form.append('overlap_ms', String(0));
      try {
        await fetch(`/api/lesson/${lessonId}/stream/chunk`, { method: 'POST', body: form });
      } catch (err) {
        console.error('Błąd wysyłki fragmentu:', err);
      }
      if (isRecording) {
        // natychmiast kolejny segment
        setTimeout(recordSegment, 0);
      }
    };
    segmentRecorder.start();
    setTimeout(() => {
      if (segmentRecorder && segmentRecorder.state === 'recording') segmentRecorder.stop();
    }, segmentMs);
  };

  recordSegment();

  // Polluj tekst na żywo co 1.5 s
  const liveText = document.getElementById('liveText');
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
});

stopBtn.addEventListener('click', () => {
  isRecording = false;
  if (segmentRecorder && segmentRecorder.state !== 'inactive') {
    try { segmentRecorder.stop(); } catch {}
  }
  if (fullRecorder && fullRecorder.state !== 'inactive') {
    try { fullRecorder.stop(); } catch {}
  }
  if (streamRef) {
    streamRef.getTracks().forEach(t => t.stop());
    streamRef = null;
  }
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
  startBtn.disabled = false;
  stopBtn.disabled = true;
  // domknij sesję (opcjonalnie)
  const lessonCtx = document.getElementById('lessonCtx');
  const lessonId = lessonCtx?.dataset?.lessonId;
  if (liveId && lessonId) {
    fetch(`/api/lesson/${lessonId}/stream/stop`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ live_id: liveId }) });
  }
});

uploadBtn.addEventListener('click', async () => {
  // prześlij pełny zapis
  const blob = new Blob(fullChunks, { type: 'audio/webm' });
  const filename = `nagranie_${Date.now()}.webm`;
  const form = new FormData();
  form.append('audio', blob, filename);

  uploadBtn.disabled = true; uploadBtn.textContent = 'Wysyłam...';
  const lessonCtx = document.getElementById('lessonCtx');
  const lessonId = lessonCtx?.dataset?.lessonId;
  try {
    const res = await fetch(`/api/lesson/${lessonId}/record/upload`, { method: 'POST', body: form });
    const data = await res.json();
    if (data.error) { alert(data.error); uploadBtn.disabled = false; uploadBtn.textContent = 'Wyślij i transkrybuj'; return; }

    // Po zapisie – od razu transkrypcja
    const tRes = await fetch(`/api/audio/${data.audio_id}/transcribe`, { method: 'POST' });
    const tData = await tRes.json();
    if (tData.error) { alert(tData.error); }
    else { alert('Transkrypcja zakończona. Odśwież stronę lekcji.'); }
  } catch (e) {
    alert('Błąd: ' + e.message);
  } finally {
    uploadBtn.disabled = false; uploadBtn.textContent = 'Wyślij i transkrybuj';
  }
});
