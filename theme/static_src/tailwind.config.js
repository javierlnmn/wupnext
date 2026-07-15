/**
 * This is a minimal config.
 *
 * If you need the full config, get it from here:
 * https://unpkg.com/browse/tailwindcss@latest/stubs/defaultConfig.stub.js
 */

module.exports = {
    darkMode: 'selector',
    content: [
        /**
         * HTML. Paths to Django template files that will contain Tailwind CSS classes.
         */

        /*  Templates within theme app (<tailwind_app_name>/templates), e.g. base.html. */
        '../templates/**/*.html',

        /*
         * Main templates directory of the project (BASE_DIR/templates).
         * Adjust the following line to match your project structure.
         */
        '../../templates/**/*.html',

        /*
         * Templates in other django apps (BASE_DIR/<any_app_name>/templates).
         * Adjust the following line to match your project structure.
         */
        '../../**/templates/**/*.html',

        /**
         * JS: If you use Tailwind CSS in JavaScript, uncomment the following lines and make sure
         * patterns match your project structure.
         */
        /* JS 1: Ignore any JavaScript in node_modules folder. */
        // '!../../**/node_modules',
        /* JS 2: Process all JavaScript files in the project. */
        // '../../**/*.js',

        /**
         * Python: If you use Tailwind CSS classes in Python, uncomment the following line
         * and make sure the pattern below matches your project structure.
         */
        // '../../**/*.py'
    ],
    theme: {
        extend: {
            fontFamily: {
                sans: ['Manrope', 'sans-serif'],
            },
            colors: {
                denim: {
                    50: '#f4f6fb',
                    100: '#e6ebf6',
                    200: '#ccd6ec',
                    300: '#abbadd',
                    400: '#8598c8',
                    500: '#6b80b3',
                    600: '#566a9b',
                    700: '#46567e',
                    800: '#3a4767',
                    900: '#313c54',
                },
                coral: {
                    50: '#fdf4ef',
                    100: '#fbe5da',
                    200: '#f6c9ae',
                    300: '#efa87d',
                    400: '#e69062',
                    500: '#e08a5b',
                    600: '#c06f43',
                    700: '#995836',
                    800: '#7a472e',
                    900: '#653c28',
                },
                olive: {
                    50: '#f6f7f1',
                    100: '#e9edde',
                    200: '#d2dab9',
                    300: '#b7c592',
                    400: '#9fb279',
                    500: '#8a9b6e',
                    600: '#71805a',
                    700: '#5a6547',
                    800: '#49523a',
                    900: '#3d4431',
                },
            },
        },
    },
    plugins: [
        /**
         * '@tailwindcss/forms' is the forms plugin that provides a minimal styling
         * for forms. If you don't like it or have own styling for forms,
         * comment the line below to disable '@tailwindcss/forms'.
         */
        require('@tailwindcss/forms'),
        require('@tailwindcss/typography'),
        require('@tailwindcss/aspect-ratio'),
    ],
}
