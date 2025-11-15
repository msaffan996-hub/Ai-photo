// static/js/capture.js
async function startCamera() {
  const video = document.getElementById('video');
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    video.srcObject = stream;
    video.play();
  } catch (err) {
    alert('لا يمكن الوصول إلى الكاميرا: ' + err);
  }
}

function takeSnapshot() {
  const video = document.getElementById('video');
  const canvas = document.createElement('canvas');
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  const dataURL = canvas.toDataURL('image/png');

  // عرض الصورة محليًا
  document.getElementById('snapshot').src = dataURL;

  // إرسالها للـ backend
  fetch('/upload_capture', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'image_data=' + encodeURIComponent(dataURL)
  }).then(r => r.json()).then(data => {
    // إعادة توجيه لصفحة الاختيار مع اسم الصورة الملتقطة
    const capture = data.capture;
    // ضع اسم الصورة في عنصر مخفي ثم توجه للصفحة التالية
    // سنحاول التوجيه مباشرة لاختيار الهدف:
    window.location.href = '/select?capture=' + encodeURIComponent(capture);
  }).catch(err => {
    alert('خطأ أثناء رفع الصورة: ' + err);
  });
}

window.addEventListener('load', () => {
  const video = document.getElementById('video');
  if (video) startCamera();
  const btn = document.getElementById('snapBtn');
  if (btn) btn.addEventListener('click', takeSnapshot);
});
