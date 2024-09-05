// Remove broken image icon for thumbnail images which don't load

// Wait for the DOM content to be fully loaded before executing the script
document.addEventListener("DOMContentLoaded", function(event) {
    // Select all <img> elements in the document
    document.querySelectorAll('img').forEach(function(img) {
        // Attach an event handler to the 'onerror' event of each <img> element
        img.onerror = function() {
            // When an image fails to load, set its display style to 'none' to hide it
            this.style.display = 'none';
        };
    });
});

// Toggle button to show and hide content for results items

// Get references to all toggle buttons and hidden content elements as arrays
const toggleButtons = document.querySelectorAll('.toggle-button');
const hiddenContents = document.querySelectorAll('.hidden-content');

// Add click event listeners to each toggle button
toggleButtons.forEach((button, index) => {
    button.addEventListener('click', function () {
        // Toggle the "hidden-content" css class to show/hide the content
        hiddenContents[index].classList.toggle('hidden-content');
        // Toggle presence of active css class on the button
        button.classList.toggle('active');
    });
    
    // Initially, remove the 'hidden-content' class and add 'active' class so text set to visible
    hiddenContents[index].classList.remove('hidden-content');
    button.classList.add('active');
});


// Remove items from search queries list

// Add event listener to the document for click events
document.addEventListener('click', function(event) {
    // Check if the clicked element or its parent has the close-button class
    var closeButton = event.target.closest('.close-button');
    if (closeButton) {
        // Get the key from the data-key attribute of the clicked button
        var key = closeButton.dataset.key;
        // Call the removeItem function with the key value
        removeItem(key);
    }
});

// Remove search queries and update the results
function removeItem(key) {
    // Construct the item id
    var itemId = key + "_param_item";

    // Get the item element using itemID
    var itemElement = document.getElementById(itemId);

    // Remove the section using item Element
    if (itemElement) {
        itemElement.parentNode.removeChild(itemElement);
    }

    // Set the value of search query for the parameter back to '*'
    var valueElement = document.getElementById(key + "_param_value");
    if (valueElement) {
        valueElement.innerText = '*';
    }

    // Trigger updateResults function for section with its key
    updateResults(key);
}

// Takes key for removed item and uses it to update key in URL query string
function updateResults(key) {
    // Get current URL
    var currentUrl = window.location.href;
    
    // Create URL object for working with URL
    var urlObject = new URL(currentUrl);
    
    // Update value for key to wildcard to show all for that parameter
    urlObject.searchParams.set(key, '*');
    
    // Redirect browser to new URL
    window.location.href = urlObject.href;
}

// More button for sidebar sections

// Listens for click event across document
document.addEventListener("click", function(event) {
    // If clicked event has "more-button" class trigger toggleSection function
    if (event.target.classList.contains("more-button")) {
        toggleSection(event.target);
    }
});

//Toggle visibility of items depending on "Show More" or "Show Less" button
function toggleSection(button) {
    // Extract the section ID from the button's data attribute
    var sectionId = button.dataset.section;

    // Find the corresponding content section using the section ID
    var itemList = document.querySelector('[data-section="' + sectionId + '"]');
    
    // Toggle the visibility of the content section by adding/removing the "show-all-items" class
    itemList.classList.toggle("show-all-items");

    // Update button text dynamically, to say "Show More" or "Show Less"
    var buttonText = button.textContent;
    button.textContent = buttonText === "Show More" ? "Show Less" : "Show More";

    // Check the number of items in the list
    var itemElements = itemList.querySelectorAll('.list-group-item');
    var numItems = itemElements.length;

    // Hide the button if the list has 5 or fewer items as no need to expand
    if (numItems <= 5) {
        button.style.display = 'none';
    } else {
        button.style.display = 'block';
    }
}

// Iterate through all buttons with class "more-button" and hide buttons if 5 or fewer items

document.addEventListener("DOMContentLoaded", function() {
    // Run this code when the DOM is fully loaded
    
    // Select all the buttons with the "more-button" class stores them in "buttons"
    var buttons = document.querySelectorAll('.more-button');

    // Iterates through each button
    buttons.forEach(function(button) {
        // Find corresponding content section items with "data-section" attribute
        var sectionId = button.dataset.section;
        var itemList = document.querySelector('[data-section="' + sectionId + '"]');

        // Check if itemList is not null before proceeding
        if (itemList !== null) {
            // Count items in section
            var itemElements = itemList.querySelectorAll('.list-group-item');
            var numItems = itemElements.length;

            // Hide the button if the list has 5 or fewer items
            if (numItems <= 5) {
                button.style.display = 'none';
            }
        // If no content section found return error message    
        } else {
            console.error('Element with data-section="' + sectionId + '" not found.');
        }
    });
});
