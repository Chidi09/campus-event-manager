// static/js/theme_toggle.js
document.addEventListener('DOMContentLoaded', () => {
    console.log('Theme toggle script: DOMContentLoaded event fired.'); // 1. Is the script running?

    const themeToggleButtons = document.querySelectorAll('.theme-toggle-button');
    const body = document.body;
    
    if (!body) {
        console.error('Theme toggle script: Body element not found!');
        return;
    }
    
    if (themeToggleButtons.length === 0) {
        console.warn('Theme toggle script: No elements found with class "theme-toggle-button".'); // 2. Are buttons found?
        // If you used an ID for a single button, e.g., id="theme-toggle", use:
        // const themeToggleButton = document.getElementById('theme-toggle');
        // if (!themeToggleButton) console.warn('Theme toggle script: Button with id "theme-toggle" not found.');
        // And then adjust the event listener part accordingly.
    } else {
        console.log(`Theme toggle script: Found ${themeToggleButtons.length} toggle button(s).`);
    }

    // Function to apply the theme
    function applyTheme(theme) {
        console.log('Theme toggle script: applyTheme called with theme =', theme); // 4. Is applyTheme being called?
        if (theme === 'dark') {
            body.classList.add('dark-mode');
            console.log('Theme toggle script: Added "dark-mode" class to body.');
        } else {
            body.classList.remove('dark-mode');
            console.log('Theme toggle script: Removed "dark-mode" class from body.');
        }
    }

    // Apply saved theme on initial load
    const storedTheme = localStorage.getItem('theme');
    console.log('Theme toggle script: Stored theme on load =', storedTheme);

    if (storedTheme) {
        applyTheme(storedTheme);
    } else {
        // Optional: Check for prefers-color-scheme if no theme is saved
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            console.log('Theme toggle script: OS prefers dark scheme.');
            applyTheme('dark');
            localStorage.setItem('theme', 'dark'); // Save the detected preference
        } else {
            console.log('Theme toggle script: Defaulting to light scheme.');
            applyTheme('light');
        }
    }

    // Add event listener to all toggle buttons
    themeToggleButtons.forEach(button => {
        button.addEventListener('click', () => {
            console.log('Theme toggle script: Button clicked!'); // 3. Is the click event firing?
            let newTheme;
            if (body.classList.contains('dark-mode')) {
                newTheme = 'light';
            } else {
                newTheme = 'dark';
            }
            applyTheme(newTheme);
            localStorage.setItem('theme', newTheme); // Save the new theme preference
            console.log('Theme toggle script: New theme preference saved =', newTheme);
        });
    });
});