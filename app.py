import base64
from textwrap import dedent

import streamlit as st
import streamlit.components.v1 as components


st.set_page_config(
    page_title="Dino Runner",
    page_icon="🦖",
    layout="centered",
)


DEFAULT_CHARACTER_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 260 340">
  <g fill="#fff" stroke="#000" stroke-width="6" stroke-linecap="round" stroke-linejoin="round">
    <path d="M40 52
             C55 32, 115 34, 178 34
             C207 32, 218 36, 230 54
             C236 65, 237 79, 229 91
             C222 101, 214 110, 214 122
             C214 136, 223 146, 227 159
             C233 177, 226 192, 209 201
             C194 209, 180 209, 170 217
             C162 224, 164 241, 167 254
             C170 267, 162 276, 149 281
             C131 288, 106 287, 81 283
             C61 280, 39 270, 27 251
             C16 233, 17 212, 20 198
             C23 183, 26 168, 21 158
             C15 146, 15 136, 25 126
             C34 118, 31 108, 22 101
             C10 91, 11 76, 21 65
             C27 58, 31 56, 40 52Z" />
    <path d="M183 56
             C196 38, 213 34, 226 40
             C239 46, 247 61, 246 77
             C245 94, 235 108, 223 116
             C212 124, 194 123, 183 114
             C171 104, 169 88, 174 75
             C177 68, 180 61, 183 56Z" />
    <ellipse cx="219" cy="80" rx="15" ry="23" fill="#000" />
    <path d="M181 124 C188 143, 193 162, 195 180" />
    <path d="M184 182 C198 188, 210 187, 227 176" />
    <path d="M64 285
             C59 300, 60 314, 64 327
             L107 327
             C107 317, 97 313, 88 311
             L88 258
             C80 256, 72 265, 69 274Z" />
    <path d="M140 283
             C145 300, 145 316, 140 329
             L212 329
             C213 321, 204 318, 197 315
             C191 313, 182 311, 176 311
             C178 297, 178 282, 171 270
             C161 266, 150 270, 144 277Z" />
    <path d="M72 239
             C82 246, 92 247, 101 243
             C95 250, 93 257, 96 266
             C102 278, 97 287, 85 292" />
    <path d="M34 160 C27 158, 18 160, 13 169 C18 179, 28 180, 36 174" />
    <path d="M21 200 C14 198, 8 202, 6 211 C11 218, 20 220, 28 216" />
  </g>
</svg>
""".strip()


def image_to_data_url(uploaded_file) -> str | None:
    if uploaded_file is None:
        encoded = base64.b64encode(DEFAULT_CHARACTER_SVG.encode("utf-8")).decode("utf-8")
        return f"data:image/svg+xml;base64,{encoded}"

    encoded = base64.b64encode(uploaded_file.getvalue()).decode("utf-8")
    return f"data:{uploaded_file.type};base64,{encoded}"


st.title("Mudkip Runner")


with st.sidebar:
    st.header("Pengaturan")
    avatar = st.file_uploader(
        "Upload karakter",
        type=["png", "jpg", "jpeg", "webp"],
        help="Kalau belum ada aset, game tetap jalan dengan karakter default.",
    )
    speed = st.slider("Kecepatan awal", min_value=6, max_value=14, value=8)
    jump_power = st.slider("Tinggi lompatan", min_value=12, max_value=22, value=16)
    st.markdown(
        """
        **Kontrol**

        - `Space` / `Arrow Up`: lompat
        - Klik area game: mulai atau lompat
        - `R`: restart setelah kalah
        """
    )

character_data_url = image_to_data_url(avatar)

components.html(
    dedent(
        f"""
        <div id="game-shell">
          <canvas id="game" width="920" height="320"></canvas>
        </div>

        <script>
          const canvas = document.getElementById("game");
          const ctx = canvas.getContext("2d");
          const width = canvas.width;
          const height = canvas.height;
          const AudioCtx = window.AudioContext || window.webkitAudioContext;
          let audioContext = null;

          const config = {{
            baseSpeed: {speed},
            jumpPower: {jump_power},
            gravity: 0.85,
          }};

          const characterImageSrc = {repr(character_data_url)};
          let characterImage = null;

          if (characterImageSrc) {{
            characterImage = new Image();
            characterImage.src = characterImageSrc;
          }}

          const groundY = height - 56;
          const player = {{
            x: 90,
            y: groundY - 54,
            width: 54,
            height: 54,
            velocityY: 0,
            grounded: true,
            rotation: 0,
          }};

          let gameStarted = false;
          let gameOver = false;
          let score = 0;
          let bestScore = 0;
          let speedNow = config.baseSpeed;
          let frameCount = 0;
          let obstacleTimer = 0;
          let particles = [];
          let obstacles = [];
          let groundOffset = 0;
          let lastMilestone = 0;

          function ensureAudio() {{
            if (!AudioCtx) {{
              return null;
            }}

            if (!audioContext) {{
              audioContext = new AudioCtx();
            }}

            if (audioContext.state === "suspended") {{
              audioContext.resume();
            }}

            return audioContext;
          }}

          function playTone(frequency, duration, type, volume, glideTo = null) {{
            const ac = ensureAudio();
            if (!ac) {{
              return;
            }}

            const now = ac.currentTime;
            const oscillator = ac.createOscillator();
            const gain = ac.createGain();

            oscillator.type = type;
            oscillator.frequency.setValueAtTime(frequency, now);
            if (glideTo !== null) {{
              oscillator.frequency.exponentialRampToValueAtTime(glideTo, now + duration);
            }}

            gain.gain.setValueAtTime(0.0001, now);
            gain.gain.exponentialRampToValueAtTime(volume, now + 0.01);
            gain.gain.exponentialRampToValueAtTime(0.0001, now + duration);

            oscillator.connect(gain);
            gain.connect(ac.destination);
            oscillator.start(now);
            oscillator.stop(now + duration);
          }}

          function playJumpSound() {{
            playTone(420, 0.12, "square", 0.03, 620);
          }}

          function playHitSound() {{
            playTone(180, 0.22, "sawtooth", 0.05, 90);
          }}

          function playStartSound() {{
            playTone(320, 0.08, "triangle", 0.025, 420);
          }}

          function playScoreSound() {{
            playTone(740, 0.08, "square", 0.02, 860);
          }}

          function resetGame() {{
            player.y = groundY - player.height;
            player.velocityY = 0;
            player.grounded = true;
            player.rotation = 0;
            gameStarted = false;
            gameOver = false;
            score = 0;
            speedNow = config.baseSpeed;
            frameCount = 0;
            obstacleTimer = 0;
            particles = [];
            obstacles = [];
            groundOffset = 0;
            lastMilestone = 0;
          }}

          function jump() {{
            if (gameOver) {{
              playStartSound();
              resetGame();
              return;
            }}

            if (!gameStarted) {{
              gameStarted = true;
              playStartSound();
            }}

            if (player.grounded) {{
              player.velocityY = -config.jumpPower;
              player.grounded = false;
              playJumpSound();
            }}
          }}

          function spawnObstacle() {{
            const tall = Math.random() > 0.65;
            const widthVar = tall ? 26 : 34 + Math.random() * 18;
            const heightVar = tall ? 58 + Math.random() * 26 : 28 + Math.random() * 16;
            obstacles.push({{
              x: width + 24,
              y: groundY - heightVar,
              width: widthVar,
              height: heightVar,
              color: tall ? "#2b7a46" : "#4f8f58",
            }});
          }}

          function addDust() {{
            if (!player.grounded || !gameStarted || gameOver) {{
              return;
            }}

            if (Math.random() > 0.45) {{
              particles.push({{
                x: player.x + 8,
                y: groundY - 4,
                radius: 2 + Math.random() * 3,
                alpha: 0.35,
                speedX: -1 - Math.random() * 2,
                speedY: -0.2 - Math.random() * 0.8,
              }});
            }}
          }}

          function update() {{
            frameCount += 1;

            if (gameStarted && !gameOver) {{
              score += 0.12;
              speedNow += 0.0009;
              obstacleTimer -= 1;
              groundOffset = (groundOffset + speedNow) % width;

              const milestone = Math.floor(score / 100);
              if (milestone > lastMilestone) {{
                lastMilestone = milestone;
                playScoreSound();
              }}

              if (obstacleTimer <= 0) {{
                spawnObstacle();
                obstacleTimer = 48 + Math.random() * 55 - Math.min(speedNow * 1.5, 20);
              }}

              addDust();
            }}

            player.velocityY += config.gravity;
            player.y += player.velocityY;

            if (player.y >= groundY - player.height) {{
              player.y = groundY - player.height;
              player.velocityY = 0;
              player.grounded = true;
              player.rotation = 0;
            }} else {{
              player.rotation = Math.max(-0.25, player.velocityY * 0.02);
            }}

            obstacles.forEach((obstacle) => {{
              obstacle.x -= speedNow;
            }});
            obstacles = obstacles.filter((obstacle) => obstacle.x + obstacle.width > -20);

            particles.forEach((particle) => {{
              particle.x += particle.speedX;
              particle.y += particle.speedY;
              particle.alpha -= 0.014;
            }});
            particles = particles.filter((particle) => particle.alpha > 0);

            for (const obstacle of obstacles) {{
              const hitboxPadding = 6;
              const hit =
                player.x + hitboxPadding < obstacle.x + obstacle.width &&
                player.x + player.width - hitboxPadding > obstacle.x &&
                player.y + hitboxPadding < obstacle.y + obstacle.height &&
                player.y + player.height - hitboxPadding > obstacle.y;

              if (hit) {{
                gameOver = true;
                bestScore = Math.max(bestScore, Math.floor(score));
                playHitSound();
                break;
              }}
            }}
          }}

          function drawBackground() {{
            const sky = ctx.createLinearGradient(0, 0, 0, height);
            sky.addColorStop(0, "#fff7db");
            sky.addColorStop(1, "#f0c27b");
            ctx.fillStyle = sky;
            ctx.fillRect(0, 0, width, height);

            ctx.fillStyle = "rgba(255,255,255,0.45)";
            ctx.beginPath();
            ctx.arc(120, 70, 28, 0, Math.PI * 2);
            ctx.arc(150, 65, 22, 0, Math.PI * 2);
            ctx.arc(177, 72, 18, 0, Math.PI * 2);
            ctx.fill();

            ctx.beginPath();
            ctx.arc(670, 82, 32, 0, Math.PI * 2);
            ctx.arc(705, 76, 25, 0, Math.PI * 2);
            ctx.arc(738, 84, 20, 0, Math.PI * 2);
            ctx.fill();
          }}

          function drawGround() {{
            ctx.fillStyle = "#d7a86e";
            ctx.fillRect(0, groundY, width, height - groundY);
            ctx.fillStyle = "#6f4e37";
            ctx.fillRect(0, groundY, width, 4);

            ctx.strokeStyle = "rgba(111,78,55,0.45)";
            ctx.lineWidth = 2;
            for (let i = -1; i < 12; i++) {{
              const x = i * 90 - groundOffset;
              ctx.beginPath();
              ctx.moveTo(x, groundY + 14);
              ctx.lineTo(x + 42, groundY + 14);
              ctx.stroke();
            }}
          }}

          function drawPlayer() {{
            ctx.save();
            ctx.translate(player.x + player.width / 2, player.y + player.height / 2);
            ctx.rotate(player.rotation);

            if (characterImage && characterImage.complete) {{
              ctx.drawImage(
                characterImage,
                -player.width / 2,
                -player.height / 2,
                player.width,
                player.height
              );
            }} else {{
              ctx.fillStyle = "#1f3c88";
              ctx.beginPath();
              ctx.roundRect(-player.width / 2, -player.height / 2, player.width, player.height, 12);
              ctx.fill();

              ctx.fillStyle = "#ffffff";
              ctx.beginPath();
              ctx.arc(10, -8, 5, 0, Math.PI * 2);
              ctx.fill();

              ctx.fillStyle = "#111111";
              ctx.beginPath();
              ctx.arc(11, -8, 2, 0, Math.PI * 2);
              ctx.fill();

              ctx.fillStyle = "#ffd166";
              ctx.fillRect(8, 4, 15, 8);
            }}

            ctx.restore();
          }}

          function drawObstacles() {{
            obstacles.forEach((obstacle) => {{
              ctx.fillStyle = obstacle.color;
              ctx.beginPath();
              ctx.roundRect(obstacle.x, obstacle.y, obstacle.width, obstacle.height, 6);
              ctx.fill();

              ctx.fillStyle = "rgba(255,255,255,0.12)";
              ctx.fillRect(obstacle.x + 4, obstacle.y + 6, 4, obstacle.height - 12);
            }});
          }}

          function drawParticles() {{
            particles.forEach((particle) => {{
              ctx.fillStyle = `rgba(111, 78, 55, ${{particle.alpha}})`;
              ctx.beginPath();
              ctx.arc(particle.x, particle.y, particle.radius, 0, Math.PI * 2);
              ctx.fill();
            }});
          }}

          function drawHud() {{
            ctx.fillStyle = "#2f2a1f";
            ctx.font = "bold 20px Arial";
            ctx.fillText(`Score: ${{Math.floor(score)}}`, 22, 34);
            ctx.fillText(`Best: ${{bestScore}}`, 22, 60);

            if (!gameStarted && !gameOver) {{
              ctx.fillStyle = "rgba(47, 42, 31, 0.84)";
              ctx.font = "bold 26px Arial";
              ctx.fillText("Klik atau tekan Space untuk mulai", 220, 120);
            }}

            if (gameOver) {{
              ctx.fillStyle = "rgba(0,0,0,0.22)";
              ctx.fillRect(0, 0, width, height);
              ctx.fillStyle = "#fffaf0";
              ctx.fillRect(width / 2 - 185, 82, 370, 118);
              ctx.strokeStyle = "#6f4e37";
              ctx.lineWidth = 3;
              ctx.strokeRect(width / 2 - 185, 82, 370, 118);
              ctx.fillStyle = "#3d2a17";
              ctx.font = "bold 28px Arial";
              ctx.fillText("Game Over", width / 2 - 76, 122);
              ctx.font = "20px Arial";
              ctx.fillText(`Skor akhir: ${{Math.floor(score)}}`, width / 2 - 72, 152);
              ctx.fillText("Tekan R atau Space untuk ulang", width / 2 - 128, 180);
            }}
          }}

          function draw() {{
            drawBackground();
            drawGround();
            drawParticles();
            drawObstacles();
            drawPlayer();
            drawHud();
          }}

          function tick() {{
            update();
            draw();
            requestAnimationFrame(tick);
          }}

          window.addEventListener("keydown", (event) => {{
            if (event.code === "Space" || event.code === "ArrowUp") {{
              event.preventDefault();
              jump();
            }}

            if (event.key.toLowerCase() === "r" && gameOver) {{
              playStartSound();
              resetGame();
            }}
          }});

          canvas.addEventListener("click", () => {{
            jump();
          }});

          resetGame();
          tick();
        </script>

        <style>
          body {{
            margin: 0;
            background: transparent;
            font-family: Arial, sans-serif;
          }}

          #game-shell {{
            width: 100%;
            display: flex;
            justify-content: center;
          }}

          canvas {{
            width: 100%;
            max-width: 920px;
            border-radius: 18px;
            border: 3px solid #6f4e37;
            box-shadow: 0 18px 40px rgba(111, 78, 55, 0.18);
            cursor: pointer;
          }}
        </style>
        """
    ),
    height=340,
)

st.info(
    "Jika ingin pakai karakter tertentu, upload gambarnya dari sidebar."
)
