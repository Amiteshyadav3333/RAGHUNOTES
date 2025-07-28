document.addEventListener("DOMContentLoaded", () => {
  const socket = io();

  // Variables globales para el estado de la aplicación
  let mediaRecorder;
  let player;
  let currentSpeaker = 'Speaker 1';

  // --- Selectores de Elementos del DOM ---
  const spinner = document.getElementById('spinner');
  const noNotesMsg = document.getElementById('no-notes-msg');
  const notesContainer = document.getElementById('notesContainer');
  const videoUrlInput = document.getElementById('videoUrl');
  const transcribeBtn = document.getElementById('transcribeBtn');
  const speakerSelect = document.getElementById('speakerSelect');
  const startBtn = document.getElementById('startBtn');
  const stopBtn = document.getElementById('stopBtn');
  const noteTextArea = document.getElementById('noteText');
  const addNoteBtn = document.getElementById('addNoteBtn');
  const downloadTxtBtn = document.getElementById('downloadTxtBtn');
  const downloadPdfBtn = document.getElementById('downloadPdfBtn');


  // --- Listeners de Socket.IO ---
  socket.on('connect', () => {
      console.log('Conectado al servidor con ID:', socket.id);
  });

  socket.on('server_message', (data) => {
      console.log('Mensaje del servidor:', data.data);
  });

  socket.on('new_note', (note) => {
      renderNote(note);
      hideNoNotesMessage();
      // Add visual feedback for successful transcription
      console.log('New note received:', note);
  });

  socket.on('notes_updated', (notes) => {
      notesContainer.innerHTML = ''; // Limpiar notas existentes
      if (notes.length > 0) {
          notes.forEach(renderNote);
          hideNoNotesMessage();
      } else {
          showNoNotesMessage();
      }
      hideSpinner();
  });

  socket.on('transcript_error', (data) => {
      console.error('Error de transcripción:', data.error);
      // Don't show alert for every error, only log it
      // alert(`Ocurrió un error durante la transcripción: ${data.error}`);
      hideSpinner();
  });


  // --- Funciones de UI ---
  const showSpinner = () => spinner.style.display = 'flex';
  const hideSpinner = () => spinner.style.display = 'none';
  const showNoNotesMessage = () => noNotesMsg.style.display = 'block';
  const hideNoNotesMessage = () => noNotesMsg.style.display = 'none';
  
  // Video loading functions
  const showVideoLoading = () => {
      const videoLoading = document.getElementById('video-loading');
      if (videoLoading) videoLoading.style.display = 'block';
  };
  
  const hideVideoLoading = () => {
      const videoLoading = document.getElementById('video-loading');
      if (videoLoading) videoLoading.style.display = 'none';
  };

  function renderNote(note) {
      const noteEl = document.createElement('div');
      noteEl.className = 'note-entry';
      noteEl.innerHTML = `
          <div><span class="speaker-badge">${escapeHTML(note.speaker)}</span>: ${escapeHTML(note.english_text)}</div>
          <div style="color: #666; font-size: 0.9em;">${escapeHTML(note.hindi_text)}</div>
          <div class="timestamp">${note.timestamp}</div>
      `;
      notesContainer.appendChild(noteEl);
      notesContainer.scrollTop = notesContainer.scrollHeight;
  }


  // --- YouTube Player ---
  window.onYouTubeIframeAPIReady = function() {
      player = new YT.Player('player', {
          height: '360',
          width: '640',
          videoId: '',
          playerVars: {
              'autoplay': 0,
              'controls': 1,
              'rel': 0,
              'showinfo': 0,
              'modestbranding': 1,
              'fs': 1,
              'cc_load_policy': 0,
              'iv_load_policy': 3,
              'playsinline': 1,
              'origin': window.location.origin,
              'enablejsapi': 1,
              'widget_referrer': window.location.origin
          },
          events: {
              'onReady': onPlayerReady,
              'onStateChange': onPlayerStateChange,
              'onError': onPlayerError
          }
      });
  }

  function onPlayerReady(event) {
      console.log('YouTube player ready');
      // Player is ready, can now load videos
  }

  function onPlayerStateChange(event) {
      // Handle player state changes
      switch(event.data) {
          case YT.PlayerState.PLAYING:
              console.log('Video started playing');
              hideVideoLoading();
              hideSpinner();
              break;
          case YT.PlayerState.PAUSED:
              console.log('Video paused');
              break;
          case YT.PlayerState.ENDED:
              console.log('Video ended');
              break;
          case YT.PlayerState.BUFFERING:
              console.log('Video buffering...');
              showVideoLoading();
              break;
          case YT.PlayerState.CUED:
              console.log('Video cued');
              hideVideoLoading();
              hideSpinner();
              break;
      }
  }

  function onPlayerError(event) {
      console.error('YouTube player error:', event.data);
      hideSpinner();
      hideVideoLoading();
      alert('Error loading video. Please try again.');
  }

  // Preload video information for better performance
  async function preloadVideoInfo(videoId) {
      try {
          // This helps with faster video loading
          const response = await fetch(`https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=${videoId}&format=json`);
          if (response.ok) {
              const data = await response.json();
              console.log('Video info preloaded:', data.title);
          }
      } catch (error) {
          console.log('Could not preload video info:', error);
      }
  }

  // --- Audio Preview for Non-YouTube URLs ---
  let audioPlayer = null;
  let audioDownloadBtn = null;

  function isYouTubeUrl(url) {
      return /(?:youtube\.com|youtu\.be)/i.test(url);
  }

  function showAudioPlayer(audioFilePath) {
      // Remove previous audio player if any
      if (audioPlayer) audioPlayer.remove();
      if (audioDownloadBtn) audioDownloadBtn.remove();
      
      const playerContainer = document.getElementById('player-container');
      audioPlayer = document.createElement('audio');
      audioPlayer.controls = true;
      audioPlayer.style.width = '100%';
      audioPlayer.src = `/get_audio?path=${encodeURIComponent(audioFilePath)}`;
      audioPlayer.className = 'mt-3';
      playerContainer.appendChild(audioPlayer);

      audioDownloadBtn = document.createElement('a');
      audioDownloadBtn.href = `/get_audio?path=${encodeURIComponent(audioFilePath)}`;
      audioDownloadBtn.download = '';
      audioDownloadBtn.className = 'btn btn-outline-primary btn-sm mt-2';
      audioDownloadBtn.innerHTML = '<i class="bi bi-download"></i> Download Audio';
      playerContainer.appendChild(audioDownloadBtn);
  }

  function hideAudioPlayer() {
      if (audioPlayer) audioPlayer.remove();
      if (audioDownloadBtn) audioDownloadBtn.remove();
  }

  function isInstagramUrl(url) {
      return /instagram\.com\/.*(reel|p|tv)\//i.test(url);
  }
  function isFacebookUrl(url) {
      return /facebook\.com\//i.test(url);
  }

  function showInstagramEmbed(url) {
      hideAudioPlayer();
      document.getElementById('player').style.display = 'none';
      const playerContainer = document.getElementById('player-container');
      // Remove previous embed if any
      const oldEmbed = document.getElementById('insta-embed');
      if (oldEmbed) oldEmbed.remove();
      const embedDiv = document.createElement('div');
      embedDiv.id = 'insta-embed';
      embedDiv.innerHTML = `<blockquote class="instagram-media" data-instgrm-permalink="${url}" data-instgrm-version="14"></blockquote>`;
      playerContainer.appendChild(embedDiv);
      // Load Instagram embed script
      if (!window.instgrm) {
          const script = document.createElement('script');
          script.src = "https://www.instagram.com/embed.js";
          script.onload = () => window.instgrm.Embeds.process();
          document.body.appendChild(script);
      } else {
          window.instgrm.Embeds.process();
      }
  }

  function showFacebookEmbed(url) {
      hideAudioPlayer();
      document.getElementById('player').style.display = 'none';
      const playerContainer = document.getElementById('player-container');
      // Remove previous embed if any
      const oldEmbed = document.getElementById('fb-embed');
      if (oldEmbed) oldEmbed.remove();
      const embedDiv = document.createElement('div');
      embedDiv.id = 'fb-embed';
      embedDiv.innerHTML = `<div class="fb-video" data-href="${url}" data-width="500" data-show-text="false"></div>`;
      playerContainer.appendChild(embedDiv);
      // Load Facebook embed script
      if (!window.FB) {
          const script = document.createElement('script');
          script.src = "https://connect.facebook.net/en_US/sdk.js#xfbml=1&version=v16.0";
          script.onload = () => window.FB.XFBML.parse();
          document.body.appendChild(script);
      } else {
          window.FB.XFBML.parse();
      }
  }

  function clearEmbeds() {
      const insta = document.getElementById('insta-embed');
      if (insta) insta.remove();
      const fb = document.getElementById('fb-embed');
      if (fb) fb.remove();
  }

  // Update processAndLoadVideo to handle embeds
  async function processAndLoadVideo() {
      const url = videoUrlInput.value;
      if (!url) {
          alert('Por favor, introduce una URL de YouTube.');
          return;
      }
      const videoId = extractVideoId(url);
      showVideoLoading();
      showSpinner();
      hideAudioPlayer();
      clearEmbeds();
      try {
          if (isYouTubeUrl(url)) {
              preloadVideoInfo(videoId);
              if (player && player.cueVideoById) {
                  player.cueVideoById({
                      videoId: videoId,
                      suggestedQuality: 'medium'
                  });
                  document.getElementById('player').style.display = '';
              }
          } else if (isInstagramUrl(url)) {
              showInstagramEmbed(url);
          } else if (isFacebookUrl(url)) {
              showFacebookEmbed(url);
          } else {
              document.getElementById('player').style.display = 'none';
          }
          setTimeout(async () => {
      try {
          const response = await fetch('/process_video', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ url: url })
          });
          const data = await response.json();
          if (!data.success) {
              throw new Error(data.error);
          }
                  console.log('Video processed successfully');
                  if (!isYouTubeUrl(url) && !isInstagramUrl(url) && !isFacebookUrl(url) && data.audio_file) {
                      showAudioPlayer(data.audio_file);
                  }
              } catch (error) {
                  console.error('Error procesando el video:', error);
              }
          }, 1000);
      } catch (error) {
          console.error('Error loading video:', error);
          alert(`Error: ${error.message}`);
          hideSpinner();
          hideVideoLoading();
      }
  }


  // --- Grabación de Audio ---
  function startListening() {
      navigator.mediaDevices.getUserMedia({ 
          audio: {
              sampleRate: 16000, // Lower sample rate for better compatibility
              channelCount: 1,
              echoCancellation: true,
              noiseSuppression: true,
              autoGainControl: true
          } 
      })
          .then(stream => {
              // Use WebM format which is most compatible with browsers
              const audioFormats = [
                  { mimeType: 'audio/webm;codecs=opus' },
                  { mimeType: 'audio/webm' },
                  { mimeType: 'audio/ogg;codecs=opus' },
                  { mimeType: 'audio/mp4' }
              ];
              
              let mediaRecorder = null;
              
              for (let format of audioFormats) {
                  try {
                      mediaRecorder = new MediaRecorder(stream, format);
                      console.log(`Using audio format: ${format.mimeType}`);
                      break;
                  } catch (e) {
                      console.log(`Format ${format.mimeType} not supported`);
                      continue;
                  }
              }
              
              if (!mediaRecorder) {
                  // Fallback to default format
                  mediaRecorder = new MediaRecorder(stream);
                  console.log("Using default audio format");
              }
              
              window.mediaRecorder = mediaRecorder;
              mediaRecorder.start(2000); // Send data every 2 seconds for better quality

              startBtn.disabled = true;
              stopBtn.disabled = false;
              
              // Add visual feedback
              startBtn.innerHTML = '<i class="bi bi-mic-fill"></i> RECORDING...';
              startBtn.classList.add('btn-danger');
              startBtn.classList.remove('btn-success');

              mediaRecorder.addEventListener("dataavailable", event => {
                  if (event.data.size > 0) {
                      console.log(`Audio chunk size: ${event.data.size} bytes`);
                      // Send the audio data directly
                      socket.emit('audio_chunk', event.data);
                  }
              });

              mediaRecorder.onstop = () => {
                  stream.getTracks().forEach(track => track.stop());
                  console.log("Audio recording stopped");
                  
                  // Reset button state
                  startBtn.disabled = false;
                  stopBtn.disabled = true;
                  startBtn.innerHTML = '<i class="bi bi-mic"></i> ON';
                  startBtn.classList.remove('btn-danger');
                  startBtn.classList.add('btn-success');
              };
              
              console.log("Audio recording started successfully");
          })
          .catch(err => {
              console.error("Error accessing microphone:", err);
              alert("Could not access microphone. Please ensure you have given permission.");
              
              // Reset button state on error
              startBtn.disabled = false;
              stopBtn.disabled = true;
          });
  }

  function stopListening() {
      if (window.mediaRecorder && window.mediaRecorder.state !== 'inactive') {
          window.mediaRecorder.stop();
          console.log("Stopping audio recording...");
      } else {
          console.log("No active recording to stop");
          // Reset button state
          startBtn.disabled = false;
          stopBtn.disabled = true;
          startBtn.innerHTML = '<i class="bi bi-mic"></i> ON';
          startBtn.classList.remove('btn-danger');
          startBtn.classList.add('btn-success');
      }
  }


  // --- Gestión de Notas ---
  async function addManualNote() {
      const text = noteTextArea.value.trim();
      if (!text) {
          alert('El campo de la nota no puede estar vacío.');
          return;
      }
      try {
          const response = await fetch('/add_note', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ english_text: text, speaker: currentSpeaker })
          });
          const data = await response.json();
          if (data.success) {
              noteTextArea.value = ''; // Limpiar textarea
          } else {
              throw new Error(data.error || 'No se pudo añadir la nota.');
          }
      } catch (error) {
          console.error('Error al añadir nota manual:', error);
          alert(`Error: ${error.message}`);
      }
  }

  async function updateSpeaker() {
      const value = speakerSelect.value;
      if (value === 'custom') {
          const customSpeaker = prompt("Introduce el nombre del hablante:", currentSpeaker);
          if (customSpeaker && customSpeaker.trim() !== '') {
              const option = new Option(customSpeaker, customSpeaker, true, true);
              speakerSelect.add(option);
              currentSpeaker = customSpeaker;
          } else {
              speakerSelect.value = currentSpeaker; // Revertir si el usuario cancela o no introduce nada
              return;
          }
      } else {
          currentSpeaker = value;
      }
      try {
          await fetch('/update_speaker', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ speaker: currentSpeaker })
          });
      } catch (error) {
          console.error('Error al actualizar el hablante:', error);
      }
  }


  // --- Descargas ---
  function downloadNotesPDF() {
      const filename = document.getElementById('pdfFilename').value.trim() || 'notas_bilingues.pdf';
      window.location.href = `/download_pdf?filename=${encodeURIComponent(filename)}`;
  }

  async function downloadNotesTXT() {
      try {
          const response = await fetch('/get_notes');
          const notes = await response.json();
          if (notes.length === 0) {
              alert("No hay notas para descargar.");
              return;
          }
          let textContent = "Notas de la Sesión\n\n";
          notes.forEach(note => {
              textContent += `[${note.timestamp}] ${note.speaker}:\n`;
              textContent += `EN: ${note.english_text}\n`;
              textContent += `HI: ${note.hindi_text}\n\n`;
          });
          const blob = new Blob([textContent], { type: 'text/plain' });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          
          // Use custom filename
          const filename = document.getElementById('txtFilename').value.trim() || 'notas.txt';
          a.download = filename;
          
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
      } catch (error) {
          console.error('Error al descargar notas TXT:', error);
      }
  }


  // --- Utilidades ---
  /**
   * Extrae el ID de un video de varios formatos de URL de YouTube.
   * @param {string} url - La URL de YouTube.
   * @returns {string|null} El ID del video o null si no se encuentra.
   */
  function extractVideoId(url) {
      let videoId = null;
      try {
          // Intenta tratar la entrada como una URL completa
          const urlObj = new URL(url);
          const hostname = urlObj.hostname;

          if (hostname === 'youtu.be') {
              // Para URLs cortas como https://youtu.be/f9Aje_cN_CY
              videoId = urlObj.pathname.slice(1);
          } else if (hostname === 'www.youtube.com' || hostname === 'youtube.com') {
              // Para URLs estándar como https://www.youtube.com/watch?v=f9Aje_cN_CY
              videoId = urlObj.searchParams.get('v');
          }
      } catch (e) {
          // Si la URL no es válida (p. ej., solo el ID), usar regex como respaldo
          console.log("La URL no es válida, intentando con regex.");
      }

      if (!videoId) {
          // Regex de respaldo para manejar varios formatos y URLs incompletas
          const regex = /(?:v=|\/|be\/|embed\/|watch\?v=|youtu\.be\/)([A-Za-z0-9_-]{11})/;
          const match = url.match(regex);
          if (match) {
              videoId = match[1];
          }
      }
      
      // El ID del video de YouTube siempre tiene 11 caracteres.
      // Esto ayuda a limpiarlo de parámetros adicionales como '?si='
      return videoId ? videoId.substring(0, 11) : null;
  }

  function escapeHTML(str) {
      const p = document.createElement("p");
      p.appendChild(document.createTextNode(str));
      return p.innerHTML;
  }


  // --- AI Features ---
  async function aiSummarize() {
      try {
          const response = await fetch('/ai_summarize', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' }
          });
          const data = await response.json();
          
          if (data.success) {
              showAIResult('✨ Resumen de Notas', data.summary);
          } else {
              alert(`Error: ${data.error}`);
          }
      } catch (error) {
          console.error('Error en resumen AI:', error);
          alert('Error al generar resumen');
      }
  }

  async function aiTitle() {
      try {
          const response = await fetch('/ai_title', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' }
          });
          const data = await response.json();
          
          if (data.success) {
              showAIResult('✨ Título Generado', `Título sugerido:\n\n${data.title}`);
          } else {
              alert(`Error: ${data.error}`);
          }
      } catch (error) {
          console.error('Error en título AI:', error);
          alert('Error al generar título');
      }
  }

  async function aiVideoAnalysis() {
      const url = videoUrlInput.value;
      if (!url) {
          alert('Por favor, introduce una URL de YouTube primero.');
          return;
      }
      
      try {
          const response = await fetch('/ai_video_analysis', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ url: url })
          });
          const data = await response.json();
          
          if (data.success) {
              const analysis = data.analysis;
              let content = `📹 Análisis del Video:\n\n`;
              content += `🎬 Título: ${analysis.title}\n`;
              content += `⏱️ Duración: ${Math.floor(analysis.duration / 60)}:${(analysis.duration % 60).toString().padStart(2, '0')} minutos\n`;
              content += `👁️ Vistas: ${analysis.view_count.toLocaleString()}\n`;
              content += `📅 Fecha: ${analysis.upload_date}\n`;
              content += `🏷️ Tags: ${analysis.tags.join(', ')}\n\n`;
              content += `📝 Descripción:\n${analysis.description}`;
              
              showAIResult('✨ Análisis del Video', content);
          } else {
              alert(`Error: ${data.error}`);
          }
      } catch (error) {
          console.error('Error en análisis AI:', error);
          alert('Error al analizar video');
      }
  }

  function showAIResult(title, content) {
      const modal = new bootstrap.Modal(document.getElementById('aiResultModal'));
      document.getElementById('aiResultModalLabel').textContent = title;
      document.getElementById('aiResultBody').textContent = content;
      modal.show();
  }

  // --- Asignación de Eventos ---
  transcribeBtn.addEventListener('click', processAndLoadVideo);
  startBtn.addEventListener('click', startListening);
  stopBtn.addEventListener('click', stopListening);
  addNoteBtn.addEventListener('click', addManualNote);
  speakerSelect.addEventListener('change', updateSpeaker);
  downloadTxtBtn.addEventListener('click', downloadNotesTXT);
  downloadPdfBtn.addEventListener('click', downloadNotesPDF);
  
  // AI Event Listeners
  document.getElementById('summarizeBtn').addEventListener('click', aiSummarize);
  document.getElementById('titleBtn').addEventListener('click', aiTitle);
  document.getElementById('actionsBtn').addEventListener('click', aiVideoAnalysis);


  // Cargar notas iniciales (si las hay)
  async function loadInitialNotes() {
      try {
          const response = await fetch('/get_notes');
          const notes = await response.json();
          if (notes.length > 0) {
              notes.forEach(renderNote);
              hideNoNotesMessage();
          }
      } catch (error) {
          console.error("No se pudieron cargar las notas iniciales:", error);
      }
  }

  loadInitialNotes();
});
