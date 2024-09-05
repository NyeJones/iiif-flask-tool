// mirador-setup.js

function initializeMirador() {
    // extract the manifest URL from the query parameter
    const urlParams = new URLSearchParams(window.location.search);
    const manifestUrl = urlParams.get("manifest");

    // check if a manifest URL is provided
    if (manifestUrl) {
        // Initialize the Mirador viewer with the manifest URL
        const mirador = Mirador.viewer({
            "id": "my-mirador",
            "manifests": {
                [manifestUrl]: {} // use the manifest URL as the key
            },
            "windows": [
                {
                    "loadedManifest": manifestUrl,
                    "thumbnailNavigationPosition": "far-bottom"
                }
            ]
        });
    } else {
        console.error("No manifest URL provided.");
    }
}

// call the initialization function
initializeMirador();
