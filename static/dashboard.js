let photos = [];
let photoIndex = 0;

// Initialize slideshow by fetching image configurations from backend
async function initSlideshow() {
    try {
        const response = await fetch('/api/photos');
        photos = await response.json();
        if (photos.length > 0) {
            changePhoto();
            setInterval(changePhoto, 10000); // Changes image every 5 seconds
        }
    } catch (err) {
        console.error("Failed to load background photo array:", err);
    }
}

function changePhoto() {
    if (photos.length === 0) return;
    const targetElement = document.getElementById('photo-panel');
    targetElement.style.backgroundImage = `url('/photos/${photos[photoIndex]}')`;
    photoIndex = (photoIndex + 1) % photos.length;
}

// Pull sensor updates directly from the shared json file
async function fetchSensorStream() {
    try {
        const response = await fetch('/sensors.json');
        const data = await response.json();
        const container = document.getElementById('sensor-container');
        
        let markupString = '';
        for (const [key, sensor] of Object.entries(data)) {
            const date = new Date(sensor.timestamp * 1000);
            const time = date.toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
                hour12: false
            });

            markupString += `
                <div class="sensor-card">
                    <div class="sensor-label">${key.replace(/_/g, ' ')} (${time})</div>
                    <div class="sensor-value">${sensor.value}</div>
                </div>
            `;
        }
        container.innerHTML = markupString;
    } catch (err) {
        console.error("Failed to parse live telemetry stream:", err);
    }
}

async function checkRemoteRefreshFlag() {
    try {
        const response = await fetch('/api/check-refresh');
        const status = await response.text();
        
        if (status.trim() === "true") {
            console.log("Remote refresh request detected. Reloading assets...");
            // true forces a hard refresh from the server, ignoring local browser cache
            window.location.reload(true); 
        }
    } catch (err) {
        // Silently catch network drops during a server restart
    }
}

// Check for developer refresh commands every 3 seconds
setInterval(checkRemoteRefreshFlag, 3000);

// Run client loops automatically when script executes
initSlideshow();
fetchSensorStream();
setInterval(fetchSensorStream, 2000); // Check for updated data every 2 seconds
