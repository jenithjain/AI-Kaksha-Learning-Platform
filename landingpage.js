import * as THREE from "three"
import { OrbitControls } from "three/addons/controls/OrbitControls.js"
import { gsap } from "gsap"
import { ScrollTrigger } from "https://unpkg.com/gsap@3.12.4/ScrollTrigger.js"

gsap.registerPlugin(ScrollTrigger)

// Mobile menu toggle
const menuToggle = document.querySelector(".menu-toggle")
const navLinks = document.querySelector(".nav-links")

if (menuToggle) {
  menuToggle.addEventListener("click", () => {
    menuToggle.classList.toggle("active")
    navLinks.classList.toggle("active")
  })
}

// Header scroll effect
const header = document.querySelector("header")
window.addEventListener("scroll", () => {
  if (window.scrollY > 50) {
    header.classList.add("scrolled")
  } else {
    header.classList.remove("scrolled")
  }
})

// Scroll animations
const animateOnScroll = () => {
  gsap.utils.toArray(".feature-card").forEach((card, i) => {
    gsap.from(card, {
      y: 50,
      opacity: 0,
      duration: 0.8,
      ease: "power2.out",
      scrollTrigger: {
        trigger: card,
        start: "top 80%",
        toggleActions: "play none none none",
      },
      delay: i * 0.2,
    })
  })

  gsap.utils.toArray(".card").forEach((card, i) => {
    gsap.from(card, {
      y: 50,
      opacity: 0,
      duration: 0.8,
      ease: "power2.out",
      scrollTrigger: {
        trigger: card,
        start: "top 80%",
        toggleActions: "play none none none",
      },
      delay: i * 0.2,
    })
  })

  gsap.from(".section-header", {
    y: 50,
    opacity: 0,
    duration: 1,
    ease: "power2.out",
    scrollTrigger: {
      trigger: ".section-header",
      start: "top 80%",
      toggleActions: "play none none none",
    },
  })

  gsap.from(".try-content", {
    y: 50,
    opacity: 0,
    duration: 1,
    ease: "power2.out",
    scrollTrigger: {
      trigger: ".try-content",
      start: "top 80%",
      toggleActions: "play none none none",
    },
  })

  gsap.from(".try-cta", {
    y: 50,
    opacity: 0,
    duration: 1,
    ease: "power2.out",
    scrollTrigger: {
      trigger: ".try-cta",
      start: "top 80%",
      toggleActions: "play none none none",
    },
    delay: 0.3,
  })
}

// Initialize 3D scenes
const initHero3D = () => {
  const container = document.getElementById("hero-3d")
  if (!container) return

  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(75, container.clientWidth / container.clientHeight, 0.1, 1000)
  camera.position.z = 5

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
  renderer.setSize(container.clientWidth, container.clientHeight)
  renderer.setPixelRatio(window.devicePixelRatio)
  renderer.outputEncoding = THREE.sRGBEncoding
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1
  container.appendChild(renderer.domElement)

  // Add ambient light
  const ambientLight = new THREE.AmbientLight(0x404040, 2)
  scene.add(ambientLight)

  // Add directional light
  const directionalLight = new THREE.DirectionalLight(0xffffff, 2)
  directionalLight.position.set(1, 1, 1)
  scene.add(directionalLight)

  // Create brain model with particles
  const particleCount = 3000
  const brainRadius = 2
  const brainGeometry = new THREE.BufferGeometry()
  const positions = new Float32Array(particleCount * 3)
  const colors = new Float32Array(particleCount * 3)
  const sizes = new Float32Array(particleCount)

  const color = new THREE.Color()
  for (let i = 0; i < particleCount; i++) {
    // Create points in a spherical shape
    const theta = Math.random() * Math.PI * 2
    const phi = Math.acos(2 * Math.random() - 1)
    const radius = brainRadius * (0.8 + Math.random() * 0.2)

    positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta)
    positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta)
    positions[i * 3 + 2] = radius * Math.cos(phi)

    // Add some variation to create brain-like shape
    if (Math.random() > 0.5) {
      positions[i * 3] *= 1.2
      positions[i * 3 + 1] *= 0.8
    }

    // Color gradient from primary to secondary
    const mixFactor = Math.random()
    color.setStyle("#4468F2").lerp(new THREE.Color("#B9D9FF"), mixFactor)

    colors[i * 3] = color.r
    colors[i * 3 + 1] = color.g
    colors[i * 3 + 2] = color.b

    sizes[i] = Math.random() * 0.1 + 0.03
  }

  brainGeometry.setAttribute("position", new THREE.BufferAttribute(positions, 3))
  brainGeometry.setAttribute("color", new THREE.BufferAttribute(colors, 3))
  brainGeometry.setAttribute("size", new THREE.BufferAttribute(sizes, 1))

  const particleMaterial = new THREE.ShaderMaterial({
    vertexShader: `
            attribute float size;
            varying vec3 vColor;
            void main() {
                vColor = color;
                vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
                gl_PointSize = size * (300.0 / -mvPosition.z);
                gl_Position = projectionMatrix * mvPosition;
            }
        `,
    fragmentShader: `
            varying vec3 vColor;
            void main() {
                float distance = length(gl_PointCoord - vec2(0.5, 0.5));
                if (distance > 0.5) discard;
                gl_FragColor = vec4(vColor, 1.0 - (distance * 2.0));
            }
        `,
    transparent: true,
    vertexColors: true,
  })

  const brainParticles = new THREE.Points(brainGeometry, particleMaterial)
  scene.add(brainParticles)

  // Add connections between particles
  const connectionsMaterial = new THREE.LineBasicMaterial({
    color: 0x4468f2,
    transparent: true,
    opacity: 0.2,
  })

  const connectionsGeometry = new THREE.BufferGeometry()
  const connectionsPositions = []

  // Create connections between nearby particles
  for (let i = 0; i < particleCount; i++) {
    const x1 = positions[i * 3]
    const y1 = positions[i * 3 + 1]
    const z1 = positions[i * 3 + 2]

    for (let j = i + 1; j < particleCount; j++) {
      const x2 = positions[j * 3]
      const y2 = positions[j * 3 + 1]
      const z2 = positions[j * 3 + 2]

      const distance = Math.sqrt(Math.pow(x2 - x1, 2) + Math.pow(y2 - y1, 2) + Math.pow(z2 - z1, 2))

      // Only connect particles that are close to each other
      if (distance < 0.7 && Math.random() > 0.95) {
        connectionsPositions.push(x1, y1, z1)
        connectionsPositions.push(x2, y2, z2)
      }
    }
  }

  connectionsGeometry.setAttribute("position", new THREE.Float32BufferAttribute(connectionsPositions, 3))
  const connections = new THREE.LineSegments(connectionsGeometry, connectionsMaterial)
  scene.add(connections)

  // Add orbit controls
  const controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.05
  controls.enableZoom = false
  controls.autoRotate = true
  controls.autoRotateSpeed = 0.5

  // Animation
  const animate = () => {
    requestAnimationFrame(animate)

    // Pulse effect
    const time = Date.now() * 0.001
    brainParticles.rotation.y = time * 0.1
    connections.rotation.y = time * 0.1

    const sizes = brainGeometry.attributes.size.array
    for (let i = 0; i < particleCount; i++) {
      sizes[i] = Math.sin(time + i) * 0.03 + 0.06
    }
    brainGeometry.attributes.size.needsUpdate = true

    controls.update()
    renderer.render(scene, camera)
  }

  animate()

  // Handle window resize
  window.addEventListener("resize", () => {
    camera.aspect = container.clientWidth / container.clientHeight
    camera.updateProjectionMatrix()
    renderer.setSize(container.clientWidth, container.clientHeight)
  })
}

const initFeatures3D = () => {
  const container = document.getElementById("features-3d")
  if (!container) return

  const scene = new THREE.Scene()
  const camera = new THREE.PerspectiveCamera(75, container.clientWidth / container.clientHeight, 0.1, 1000)
  camera.position.z = 5

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
  renderer.setSize(container.clientWidth, container.clientHeight)
  renderer.setPixelRatio(window.devicePixelRatio)
  container.appendChild(renderer.domElement)

  // Add lights
  const ambientLight = new THREE.AmbientLight(0x404040, 2)
  scene.add(ambientLight)

  const directionalLight = new THREE.DirectionalLight(0xffffff, 2)
  directionalLight.position.set(1, 1, 1)
  scene.add(directionalLight)

  // Create floating cubes
  const cubes = []
  const cubeCount = 50

  for (let i = 0; i < cubeCount; i++) {
    const size = Math.random() * 0.3 + 0.1
    const geometry = new THREE.BoxGeometry(size, size, size)

    // Create gradient material
    const material = new THREE.MeshPhongMaterial({
      color: new THREE.Color(0x4468f2).lerp(new THREE.Color(0xb9d9ff), Math.random()),
      transparent: true,
      opacity: 0.7,
      shininess: 100,
    })

    const cube = new THREE.Mesh(geometry, material)

    // Position cubes in a circular pattern
    const radius = 4
    const angle = Math.random() * Math.PI * 2
    const height = (Math.random() - 0.5) * 2

    cube.position.x = Math.cos(angle) * radius * Math.random()
    cube.position.y = height
    cube.position.z = Math.sin(angle) * radius * Math.random()

    // Store initial position for animation
    cube.userData.initialPosition = {
      x: cube.position.x,
      y: cube.position.y,
      z: cube.position.z,
    }

    // Random rotation
    cube.rotation.x = Math.random() * Math.PI
    cube.rotation.y = Math.random() * Math.PI

    // Animation parameters
    cube.userData.rotationSpeed = {
      x: (Math.random() - 0.5) * 0.02,
      y: (Math.random() - 0.5) * 0.02,
      z: (Math.random() - 0.5) * 0.02,
    }

    cube.userData.floatSpeed = Math.random() * 0.01 + 0.005
    cube.userData.floatOffset = Math.random() * Math.PI * 2

    scene.add(cube)
    cubes.push(cube)
  }

  // Animation
  const animate = () => {
    requestAnimationFrame(animate)

    const time = Date.now() * 0.001

    cubes.forEach((cube) => {
      // Rotate cube
      cube.rotation.x += cube.userData.rotationSpeed.x
      cube.rotation.y += cube.userData.rotationSpeed.y
      cube.rotation.z += cube.userData.rotationSpeed.z

      // Float up and down
      const initialPos = cube.userData.initialPosition
      cube.position.y = initialPos.y + Math.sin(time * cube.userData.floatSpeed + cube.userData.floatOffset) * 0.5

      // Subtle movement in x and z
      cube.position.x = initialPos.x + Math.sin(time * cube.userData.floatSpeed * 0.7 + cube.userData.floatOffset) * 0.2
      cube.position.z = initialPos.z + Math.cos(time * cube.userData.floatSpeed * 0.7 + cube.userData.floatOffset) * 0.2
    })

    renderer.render(scene, camera)
  }

  animate()

  // Handle window resize
  window.addEventListener("resize", () => {
    camera.aspect = container.clientWidth / container.clientHeight
    camera.updateProjectionMatrix()
    renderer.setSize(container.clientWidth, container.clientHeight)
  })
}

// Initialize everything when DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
  initHero3D()
  initFeatures3D()
  animateOnScroll()

  // Smooth scrolling for anchor links
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener("click", function (e) {
      e.preventDefault()

      const targetId = this.getAttribute("href")
      if (targetId === "#") return

      const targetElement = document.querySelector(targetId)
      if (targetElement) {
        window.scrollTo({
          top: targetElement.offsetTop - 80,
          behavior: "smooth",
        })

        // Close mobile menu if open
        if (menuToggle && menuToggle.classList.contains("active")) {
          menuToggle.classList.remove("active")
          navLinks.classList.remove("active")
        }
      }
    })
  })
})

