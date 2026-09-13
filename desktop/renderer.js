/**
 * Accio Persistent Desktop Orb - Renderer Process
 * Handles delta-based dragging vs clicking, tactile feedback,
 * and push-to-talk microphone recording on right-click.
 */

document.addEventListener('DOMContentLoaded', () => {
  const overlayContainer = document.getElementById('overlayContainer');
  const accioOrb = document.getElementById('accioOrb');
  const rippleElement = document.getElementById('rippleElement');
  const statusPill = document.getElementById('statusPill');

  let isPointerDown = false;
  let isDragging = false;
  let startScreenX = 0;
  let startScreenY = 0;
  const DRAG_THRESHOLD_PX = 5;

  // Audio capture state
  let audioContext = null;
  let mediaStream = null;
  let audioInputNode = null;
  let audioProcessorNode = null;
  let recordedSamples = [];
  let isMicRecording = false;

  // Right-click hold & double-click tracking
  let rightClickTimer = null;
  let lastRightClickTime = 0;
  let isRightClickHold = false;
  const RIGHT_CLICK_HOLD_MS = 450;

  /**
   * Encodes an array of Float32 PCM audio samples into a standard 16kHz mono WAV ArrayBuffer.
   */
  function encodeWav(samples, sampleRate = 16000) {
    const buffer = new ArrayBuffer(44 + samples.length * 2);
    const view = new DataView(buffer);

    function writeString(view, offset, string) {
      for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
      }
    }

    // RIFF header
    writeString(view, 0, 'RIFF');
    view.setUint32(4, 36 + samples.length * 2, true);
    writeString(view, 8, 'WAVE');

    // "fmt " sub-chunk
    writeString(view, 12, 'fmt ');
    view.setUint32(16, 16, true);           // SubChunk1Size (16 for PCM)
    view.setUint16(20, 1, true);            // AudioFormat (1 = linear PCM)
    view.setUint16(22, 1, true);            // NumChannels (1 = mono)
    view.setUint32(24, sampleRate, true);   // SampleRate
    view.setUint32(28, sampleRate * 2, true);// ByteRate (SampleRate * NumChannels * BitsPerSample / 8)
    view.setUint16(32, 2, true);            // BlockAlign (NumChannels * BitsPerSample / 8)
    view.setUint16(34, 16, true);           // BitsPerSample (16 bits)

    // "data" sub-chunk
    writeString(view, 36, 'data');
    view.setUint32(40, samples.length * 2, true);

    // Write 16-bit PCM samples
    let offset = 44;
    for (let i = 0; i < samples.length; i++, offset += 2) {
      const s = Math.max(-1, Math.min(1, samples[i]));
      view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
    }

    return buffer;
  }

  /**
   * Starts capturing microphone audio for push-to-talk.
   */
  async function startMicRecording() {
    try {
      recordedSamples = [];
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      audioContext = new AudioCtx({ sampleRate: 16000 });

      mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 16000,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });

      audioInputNode = audioContext.createMediaStreamSource(mediaStream);
      audioProcessorNode = audioContext.createScriptProcessor(4096, 1, 1);

      audioProcessorNode.onaudioprocess = (e) => {
        if (!isMicRecording) return;
        const channelData = e.inputBuffer.getChannelData(0);
        recordedSamples.push(new Float32Array(channelData));
      };

      audioInputNode.connect(audioProcessorNode);
      audioProcessorNode.connect(audioContext.destination);

      isMicRecording = true;

      // Active listening visuals
      overlayContainer.classList.remove('is-speaking', 'is-processing');
      overlayContainer.classList.add('is-listening');
      if (statusPill) statusPill.textContent = 'Mic Live • Click to Run';

      if (window.accioDesktop && window.accioDesktop.micStateChanged) {
        window.accioDesktop.micStateChanged({ state: 'listening' });
      }
      console.log('[Accio Mic] Recording started.');
    } catch (err) {
      console.error('[Accio Mic] Microphone access error:', err);
      if (statusPill) statusPill.textContent = 'Mic Access Error';
      isMicRecording = false;
    }
  }

  /**
   * Stops microphone recording, encodes the audio buffer into WAV, and sends to Python speech engine.
   */
  async function stopMicRecordingAndExecute() {
    if (!isMicRecording) return;
    isMicRecording = false;

    // Visual transition to processing state
    overlayContainer.classList.remove('is-listening', 'is-speaking');
    overlayContainer.classList.add('is-processing');
    if (statusPill) statusPill.textContent = 'Transcribing...';

    if (window.accioDesktop && window.accioDesktop.micStateChanged) {
      window.accioDesktop.micStateChanged({ state: 'processing' });
    }

    // Teardown audio streams
    try {
      if (audioProcessorNode) audioProcessorNode.disconnect();
      if (audioInputNode) audioInputNode.disconnect();
      if (mediaStream) {
        mediaStream.getTracks().forEach((track) => track.stop());
      }
      if (audioContext && audioContext.state !== 'closed') {
        await audioContext.close();
      }
    } catch (_) {}

    // Concatenate all recorded sample chunks
    let totalLength = 0;
    for (const chunk of recordedSamples) {
      totalLength += chunk.length;
    }

    if (totalLength < 1600) {
      console.warn('[Accio Mic] Audio recording was too brief.');
      overlayContainer.classList.remove('is-processing');
      if (statusPill) statusPill.textContent = 'Accio • Speech too short';
      setTimeout(() => {
        if (statusPill) statusPill.textContent = 'Accio • Ready';
      }, 1500);
      return;
    }

    const mergedSamples = new Float32Array(totalLength);
    let writeOffset = 0;
    for (const chunk of recordedSamples) {
      mergedSamples.set(chunk, writeOffset);
      writeOffset += chunk.length;
    }

    // Encode to 16kHz mono WAV format
    const wavBuffer = encodeWav(mergedSamples, 16000);
    console.log(`[Accio Mic] Audio recorded: ${totalLength} samples (${(totalLength / 16000).toFixed(2)}s). Transcribing...`);

    try {
      if (window.accioDesktop && window.accioDesktop.executeAudio) {
        const result = await window.accioDesktop.executeAudio(wavBuffer);
        console.log('[Accio Result from Python]', result);

        if (result && result.text) {
          if (statusPill) statusPill.textContent = `You: "${result.text}"`;
          overlayContainer.classList.remove('is-processing');
          overlayContainer.classList.add('is-speaking');
          setTimeout(() => {
            overlayContainer.classList.remove('is-speaking');
            if (statusPill) statusPill.textContent = 'Accio • Ready for next';
          }, 3500);
        } else {
          overlayContainer.classList.remove('is-processing');
          if (statusPill) statusPill.textContent = 'Accio • No speech heard';
          setTimeout(() => {
            if (statusPill) statusPill.textContent = 'Accio • Ready for next';
          }, 2000);
        }
      }
    } catch (err) {
      console.error('[Accio Execution Error]', err);
      overlayContainer.classList.remove('is-processing');
      if (statusPill) statusPill.textContent = 'Accio • Error executing';
      setTimeout(() => {
        if (statusPill) statusPill.textContent = 'Accio • Ready for next';
      }, 2000);
    }
  }

  /**
   * Toggles push-to-talk microphone state.
   */
  function handleMicToggle() {
    if (!isMicRecording) {
      startMicRecording();
    } else {
      stopMicRecordingAndExecute();
    }
  }

  // Pointer Down on Core Orb (Left-click for dragging)
  accioOrb.addEventListener('pointerdown', (e) => {
    if (e.button !== 0) return;

    isPointerDown = true;
    isDragging = false;
    startScreenX = e.screenX;
    startScreenY = e.screenY;

    const offsetX = e.clientX;
    const offsetY = e.clientY;

    if (window.accioDesktop) {
      window.accioDesktop.dragStart({ x: offsetX, y: offsetY });
    }

    accioOrb.setPointerCapture(e.pointerId);
  });

  // Global Pointer Move (Window Dragging)
  window.addEventListener('pointermove', (e) => {
    if (!isPointerDown) return;

    const deltaX = e.screenX - startScreenX;
    const deltaY = e.screenY - startScreenY;
    const distanceMoved = Math.hypot(deltaX, deltaY);

    if (!isDragging && distanceMoved >= DRAG_THRESHOLD_PX) {
      isDragging = true;
      accioOrb.classList.add('is-dragging');
      if (statusPill) statusPill.textContent = 'Accio • Moving';
    }

    if (isDragging && window.accioDesktop) {
      window.accioDesktop.dragMove();
    }
  });

  // Pointer Up (End Drag / Left Click)
  window.addEventListener('pointerup', (e) => {
    if (!isPointerDown) return;

    isPointerDown = false;

    if (window.accioDesktop) {
      window.accioDesktop.dragEnd();
    }

    accioOrb.classList.remove('is-dragging');
    accioOrb.classList.remove('is-active');
    if (!isMicRecording && statusPill) statusPill.textContent = 'Accio • Ready for next';

    try {
      accioOrb.releasePointerCapture(e.pointerId);
    } catch (_) {}

    // Movement within threshold -> Left Click Event
    if (!isDragging && e.button === 0) {
      handleOrbClick(e);
    }
  });

  // Right-Click Push-to-Talk and Context Menu Handling
  // - Short Right-Click (<450ms): Toggles microphone (Click 1: Start Recording, Click 2: Stop & Execute)
  // - Long Right-Click (>450ms) or Double Right-Click: Opens native settings context menu
  accioOrb.addEventListener('mousedown', (e) => {
    if (e.button === 2) {
      isRightClickHold = false;
      rightClickTimer = setTimeout(() => {
        isRightClickHold = true;
        if (window.accioDesktop && window.accioDesktop.showContextMenu) {
          window.accioDesktop.showContextMenu();
        }
      }, RIGHT_CLICK_HOLD_MS);
    }
  });

  accioOrb.addEventListener('mouseup', (e) => {
    if (e.button === 2) {
      if (rightClickTimer) {
        clearTimeout(rightClickTimer);
        rightClickTimer = null;
      }
      if (!isRightClickHold) {
        const now = Date.now();
        if (now - lastRightClickTime < 300) {
          // Double right-click -> show settings menu
          if (window.accioDesktop && window.accioDesktop.showContextMenu) {
            window.accioDesktop.showContextMenu();
          }
        } else {
          // Single right-click -> toggle push-to-talk mic
          handleMicToggle();
        }
        lastRightClickTime = now;
      }
    }
  });

  // Prevent standard browser context menu on orb
  accioOrb.addEventListener('contextmenu', (e) => {
    e.preventDefault();
  });

  // Keyboard accessibility (Space/Enter for tactile click, 'M' key for mic push-to-talk)
  accioOrb.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleOrbClick(e);
    } else if (e.key.toLowerCase() === 'm') {
      e.preventDefault();
      handleMicToggle();
    }
  });

  function handleOrbClick(e) {
    console.log('[Accio Renderer] Orb clicked!');

    // Tactile Click Compression
    accioOrb.classList.add('is-active');
    setTimeout(() => accioOrb.classList.remove('is-active'), 180);

    // Expand Acoustic Shockwave Ripple at Click Location
    if (rippleElement) {
      const rect = accioOrb.getBoundingClientRect();
      const clickX = (e && e.clientX ? e.clientX : rect.left + rect.width / 2) - rect.left;
      const clickY = (e && e.clientY ? e.clientY : rect.top + rect.height / 2) - rect.top;

      rippleElement.style.left = `${clickX}px`;
      rippleElement.style.top = `${clickY}px`;
      rippleElement.classList.remove('animate');
      void rippleElement.offsetWidth; // Force CSS reflow
      rippleElement.classList.add('animate');
    }

    if (!isMicRecording) {
      overlayContainer.classList.add('is-speaking');
      if (statusPill) statusPill.textContent = 'Accio • Ready for next';
      setTimeout(() => {
        overlayContainer.classList.remove('is-speaking');
      }, 2500);
    }

    if (window.accioDesktop) {
      window.accioDesktop.orbClick();
    }
  }

  // Listen for state change signals from Main process
  if (window.accioDesktop && window.accioDesktop.onStateChange) {
    window.accioDesktop.onStateChange((data) => {
      console.log('[Accio Event from Main]', data);
      if (data && data.state === 'visible') {
        accioOrb.classList.remove('anim-entrance');
        void accioOrb.offsetWidth;
        accioOrb.classList.add('anim-entrance');
        setTimeout(() => accioOrb.classList.remove('anim-entrance'), 300);
      }
    });
  }

  // Dynamic Theme Switching & Persistence
  const savedTheme = localStorage.getItem('accio-orb-theme') || 'aurora';
  document.body.setAttribute('data-theme', savedTheme);

  if (window.accioDesktop && window.accioDesktop.onThemeChange) {
    window.accioDesktop.onThemeChange((newTheme) => {
      console.log('[Accio Theme Change]', newTheme);
      document.body.setAttribute('data-theme', newTheme);
      localStorage.setItem('accio-orb-theme', newTheme);
    });
  }

  // Dynamic Voice Reactive Glow State (Active Only When Speaking / Listening)
  if (window.accioDesktop && window.accioDesktop.onVoiceState) {
    window.accioDesktop.onVoiceState((data) => {
      // Don't override local push-to-talk recording state with ambient idle signals
      if (isMicRecording) return;

      const voiceState = data && data.state ? data.state : 'idle';
      const speechText = data && data.text ? data.text : '';
      const feedbackMsg = data && data.message ? data.message : '';
      console.log('[Accio Voice State]', voiceState, speechText, feedbackMsg);

      overlayContainer.classList.remove('is-listening', 'is-speaking', 'is-processing');

      if (voiceState === 'listening') {
        overlayContainer.classList.add('is-listening');
        if (statusPill) statusPill.textContent = 'Accio • Listening...';
      } else if (voiceState === 'transcribed') {
        overlayContainer.classList.add('is-processing');
        if (statusPill) statusPill.textContent = speechText ? `You: "${speechText}"` : 'Accio • Processing...';
      } else if (voiceState === 'speaking') {
        overlayContainer.classList.add('is-speaking');
        if (statusPill) statusPill.textContent = feedbackMsg ? `Accio: "${feedbackMsg}"` : 'Accio • Speaking...';
      } else if (voiceState === 'processing') {
        overlayContainer.classList.add('is-processing');
        if (statusPill) statusPill.textContent = 'Accio • Thinking...';
      } else if (voiceState === 'ready_for_next') {
        if (statusPill) statusPill.textContent = 'Accio • Ready for next';
      } else {
        if (statusPill) statusPill.textContent = 'Accio • Ready for next';
      }
    });
  }
});
