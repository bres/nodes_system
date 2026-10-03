(function () {
    const graphBg = document.getElementById('graphBackground');
    if (!graphBg) return;

    const colors = ['#ff3b5c', '#00f5a0', '#ffe66d', '#ff4ecd', '#ff8a3d', '#c77dff', '#00d9ff', '#b8ff3d', '#ffffff'];

    const prefersReduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    // Performance-tuned parameters
    const TARGET_FPS = prefersReduce ? 12 : 30;
    const SPEED_FACTOR = prefersReduce ? 0.22 : 0.65;
    const MAX_NODES = prefersReduce ? 8 : 14;
    const GRID_SIZE = 96;
    const LINE_COLOR = 'rgba(217,255,244,'; // append alpha
    const labelElement = document.getElementById('graph-labels');
    const graphLabels = labelElement ? JSON.parse(labelElement.textContent) : [];

    // Create canvas
    const canvas = document.createElement('canvas');
    canvas.style.position = 'absolute';
    canvas.style.left = '0';
    canvas.style.top = '0';
    canvas.style.width = '100%';
    canvas.style.height = '100%';
    canvas.style.opacity = '0.72';
    canvas.setAttribute('aria-hidden', 'true');
    graphBg.appendChild(canvas);

    const ctx = canvas.getContext('2d');

    let dpr = Math.max(1, window.devicePixelRatio || 1);
    let width = 0, height = 0;

    class Node {
        constructor(x, y) {
            this.x = x;
            this.y = y;
            this.renderX = x;
            this.renderY = y;
            const angle = Math.random() * Math.PI * 2;
            const speed = (Math.random() * 0.45 + 0.35) * SPEED_FACTOR;
            this.vx = Math.cos(angle) * speed;
            this.vy = Math.sin(angle) * speed;
            this.r = Math.random() < 0.06 ? Math.random() * 5 + 7 : Math.random() * 5 + 2.5;
            this.color = colors[Math.floor(Math.random() * colors.length)];
            this.label = '';
        }

        update(deltaSeconds) {
            this.x += this.vx * deltaSeconds * TARGET_FPS;
            this.y += this.vy * deltaSeconds * TARGET_FPS;
            if (this.x - this.r < 0 || this.x + this.r > width) {
                this.vx = -this.vx;
                this.x = Math.max(this.r, Math.min(width - this.r, this.x));
            }
            if (this.y - this.r < 0 || this.y + this.r > height) {
                this.vy = -this.vy;
                this.y = Math.max(this.r, Math.min(height - this.r, this.y));
            }

            const easing = Math.min(1, deltaSeconds * 12);
            this.renderX += (this.x - this.renderX) * easing;
            this.renderY += (this.y - this.renderY) * easing;
        }
    }

    let nodes = [];
    let structureLinks = [];

    function rebuildStructures() {
        structureLinks = [];
        if (nodes.length < 5 || Math.random() > 0.32) return;

        const linkKeys = new Set();
        const addLink = (first, second) => {
            if (first === second) return;
            const key = first < second ? `${first}-${second}` : `${second}-${first}`;
            if (linkKeys.has(key)) return;
            linkKeys.add(key);
            structureLinks.push([first, second]);
        };

        const hubs = [...Array(nodes.length).keys()]
            .sort(() => Math.random() - 0.5)
            .slice(0, Math.min(3, Math.max(2, Math.floor(nodes.length / 8))));

        hubs.forEach((hub, hubIndex) => {
            const spokeCount = 3 + Math.floor(Math.random() * 4);
            const candidates = [...Array(nodes.length).keys()]
                .filter(index => index !== hub && !hubs.includes(index))
                .sort(() => Math.random() - 0.5)
                .slice(0, spokeCount);
            candidates.forEach(node => addLink(hub, node));

            if (hubIndex > 0) addLink(hubs[hubIndex - 1], hub);
        });

        for (let i = 0; i < 1 + Math.floor(Math.random() * 2); i++) {
            const triangle = [...Array(nodes.length).keys()]
                .sort(() => Math.random() - 0.5)
                .slice(0, 3);
            addLink(triangle[0], triangle[1]);
            addLink(triangle[1], triangle[2]);
            addLink(triangle[2], triangle[0]);
        }
    }

    function resize() {
        const rect = graphBg.getBoundingClientRect();
        width = Math.max(0, rect.width);
        height = Math.max(0, rect.height);
        dpr = Math.max(1, window.devicePixelRatio || 1);
        canvas.width = Math.floor(width * dpr);
        canvas.height = Math.floor(height * dpr);
        canvas.style.width = width + 'px';
        canvas.style.height = height + 'px';
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

        // Recreate nodes with adjusted count to avoid huge densities
        const autoCount = Math.floor((width * height) / 110000) + 4;
        const nodeCount = Math.min(MAX_NODES, Math.max(6, autoCount));
        if (nodes.length > nodeCount) {
            nodes = nodes.slice(0, nodeCount);
        } else {
            while (nodes.length < nodeCount) {
                nodes.push(new Node(Math.random() * width, Math.random() * height));
            }
        }
        nodes.forEach((node, index) => {
            node.label = graphLabels.length
                ? graphLabels[index % graphLabels.length]
                : `Node ${index + 1}`;
        });
        rebuildStructures();
    }

    // initial resize
    resize();

    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(graphBg);

    // Draw loop with FPS cap
    let lastTime = performance.now();
    let running = true;
    document.addEventListener('visibilitychange', () => { running = !document.hidden; });

    function draw() {
        const now = performance.now();
        const delta = now - lastTime;
        if (!running) {
            lastTime = now;
            requestAnimationFrame(draw);
            return;
        }

        lastTime = now;
        const deltaSeconds = Math.min(delta, 50) / 1000;

            // Clear
            ctx.clearRect(0, 0, width, height);

            // Keep the coordinate grid stable while the graph moves over it.
            ctx.setLineDash([]);
            ctx.strokeStyle = 'rgba(217, 255, 244, 0.08)';
            ctx.lineWidth = 1;
            ctx.beginPath();
            for (let x = 0; x <= width; x += GRID_SIZE) {
                ctx.moveTo(x, 0);
                ctx.lineTo(x, height);
            }
            for (let y = 0; y <= height; y += GRID_SIZE) {
                ctx.moveTo(0, y);
                ctx.lineTo(width, y);
            }
            ctx.stroke();

            // Update positions
            for (let i = 0; i < nodes.length; i++) nodes[i].update(deltaSeconds);

            // Draw edges (simple O(n^2) but n is small)
            for (let i = 0; i < nodes.length; i++) {
                const a = nodes[i];
                for (let j = i + 1; j < nodes.length; j++) {
                    const b = nodes[j];
                    const dx = a.renderX - b.renderX;
                    const dy = a.renderY - b.renderY;
                    const dist = Math.hypot(dx, dy);
                    const maxDist = 180; // threshold
                    if (dist < maxDist) {
                        const alpha = Math.min(0.62, 0.62 * (1 - dist / maxDist));
                        ctx.strokeStyle = LINE_COLOR + alpha + ')';
                        ctx.lineWidth = 0.7 + ((i * 13 + j * 7) % 5) * 0.22;
                        if ((i * 17 + j * 11) % 5 === 0) {
                            ctx.setLineDash([4 + (j % 3), 5 + (i % 3)]);
                            ctx.lineDashOffset = 0;
                        } else {
                            ctx.setLineDash([]);
                            ctx.lineDashOffset = 0;
                        }
                        ctx.beginPath();
                        ctx.moveTo(a.renderX, a.renderY);
                        ctx.lineTo(b.renderX, b.renderY);
                        ctx.stroke();
                    }
                }
            }

            // Add a few random hubs, spokes, triangles, and cross-links.
            for (let k = 0; k < structureLinks.length; k++) {
                const [first, second] = structureLinks[k];
                const a = nodes[first];
                const b = nodes[second];
                const distance = Math.hypot(a.renderX - b.renderX, a.renderY - b.renderY);
                const alpha = Math.min(0.42, 0.42 * (1 - distance / (width + height)));
                ctx.strokeStyle = LINE_COLOR + Math.max(0.08, alpha) + ')';
                ctx.lineWidth = 0.8 + (k % 4) * 0.18;
                if (k % 4 === 0) {
                    ctx.setLineDash([5 + (k % 3), 4 + (k % 2)]);
                    ctx.lineDashOffset = 0;
                } else {
                    ctx.setLineDash([]);
                    ctx.lineDashOffset = 0;
                }
                ctx.beginPath();
                ctx.moveTo(a.renderX, a.renderY);
                ctx.lineTo(b.renderX, b.renderY);
                ctx.stroke();
            }
            ctx.setLineDash([]);

            // Draw nodes
            for (let i = 0; i < nodes.length; i++) {
                const n = nodes[i];
                ctx.beginPath();
                ctx.fillStyle = n.color;
                ctx.globalAlpha = 0.95;
                const nodeX = n.renderX;
                const nodeY = n.renderY;
                ctx.arc(nodeX, nodeY, n.r, 0, Math.PI * 2);
                ctx.fill();
                if (n.label) {
                    ctx.font = '11px DM Sans, sans-serif';
                    ctx.fillStyle = 'rgba(255, 255, 255, 0.72)';
                    ctx.fillText(n.label, nodeX + n.r + 6, nodeY - n.r - 3);
                }
            }
            ctx.globalAlpha = 1;
        requestAnimationFrame(draw);
    }

    // Inform developer if reduced motion active
    if (prefersReduce) console.info('Graph background: reduced-motion active — using low-power canvas mode');

    requestAnimationFrame(draw);
})();
