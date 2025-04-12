$(document).ready(function() {
    let table = null; // Variable to hold the DataTable instance
    let allLeadsData = []; // To store all fetched leads

    // Function to safely get nested properties
    const getSafe = (fn, defaultValue = 'N/A') => {
        try {
            const result = fn();
            // Handle null or undefined explicitly, return defaultValue
            return (result === null || typeof result === 'undefined') ? defaultValue : result;
        } catch (e) {
            return defaultValue;
        }
    };

    // Function to format date string
    const formatDate = (isoString) => {
        if (!isoString || isoString === 'N/A') return 'N/A';
        try {
            const date = new Date(isoString);
            // Format as YYYY-MM-DD HH:MM
            return date.toISOString().slice(0, 16).replace('T', ' ');
        } catch (e) {
            return 'Invalid Date';
        }
    };

    // Function to initialize or reinitialize DataTable
    function initializeDataTable(data) {
        if (table) {
            table.destroy(); // Destroy existing table if it exists
            $('#leadsTable tbody').empty(); // Clear the table body
        }

        table = $('#leadsTable').DataTable({
            data: data,
            columns: [
                { data: 'scraped_timestamp', render: formatDate },
                { data: 'date_posted_iso', render: formatDate },
                { data: 'city', defaultContent: 'N/A' },
                {
                    data: 'title',
                    render: function(data, type, row) {
                        const url = getSafe(() => row.url, '#');
                        const titleText = getSafe(() => data, 'N/A');
                        return `<a href="${url}" target="_blank">${titleText}</a>`;
                    }
                },
                { data: 'category', defaultContent: 'N/A' },
                { data: 'ai_profitability_score', defaultContent: 'N/A' }, // Access flattened field
                {
                    data: 'ai_is_junk', // Access flattened field
                    render: function(data) {
                        const isJunk = getSafe(() => data, false); // Default to false if missing/null
                        return isJunk ? 'Yes' : 'No';
                    }
                },
                {
                    data: 'ai_reasoning', // Access flattened field
                    render: function(data) {
                        const reasoning = getSafe(() => data, 'N/A');
                        // Add tooltip and ellipsis
                        return `<span class="reasoning-cell" title="${reasoning.replace(/"/g, '"')}">${reasoning}</span>`;
                    },
                    className: 'reasoning-cell' // Apply class for CSS styling
                }
                // Add more columns as needed, matching the <thead> in index.html
            ],
            order: [[ 5, "desc" ]], // Default sort by AI Score descending
            pageLength: 25, // Show 25 entries per page
            // Add other DataTables options if needed
        });
    }

    // Function to populate category filter
    function populateCategoryFilter(data) {
        const categories = new Set();
        data.forEach(lead => {
            const category = getSafe(() => lead.category, null);
            if (category && category !== 'N/A') {
                categories.add(category);
            }
        });

        const categoryFilter = $('#category-filter');
        // Clear existing options except the first 'All Categories' one
        categoryFilter.find('option:not(:first)').remove();

        categories.forEach(category => {
            categoryFilter.append($('<option>', {
                value: category,
                text: category // Display the category code directly, could map to names later
            }));
        });
    }

    // Custom filtering function
    function applyFilters() {
        const minScore = parseInt($('#min-score').val()) || 1;
        const maxScore = parseInt($('#max-score').val()) || 10;
        const junkFilter = $('#junk-filter').val(); // 'all', 'yes', 'no'
        const categoryFilter = $('#category-filter').val(); // 'all' or specific category code

        const filteredData = allLeadsData.filter(lead => {
            const score = getSafe(() => lead.ai_profitability_score, null); // Access flattened field
            const isJunk = getSafe(() => lead.ai_is_junk, false); // Access flattened field
            const category = getSafe(() => lead.category, null);

            // Score filtering (Revised Logic)
            let scoreMatch = false; // Default to false unless criteria met
            if (junkFilter === 'yes') {
                 // If specifically filtering FOR junk, include all junk regardless of score (or lack thereof)
                 if (isJunk) {
                     scoreMatch = true;
                 }
            } else {
                 // If showing 'all' or 'no' junk:
                 if (score !== null) {
                     // If score exists, check if it's within the selected range
                     scoreMatch = score >= minScore && score <= maxScore;
                 } else {
                     // If score is null, only include if the filter range is effectively "all" (1-10)
                     scoreMatch = (minScore === 1 && maxScore === 10);
                 }
            }


            // Junk filtering
            let junkMatch = true;
            if (junkFilter === 'yes') {
                junkMatch = isJunk === true;
            } else if (junkFilter === 'no') {
                junkMatch = isJunk === false;
            } // 'all' means junkMatch remains true

            // Category filtering
            let categoryMatch = true;
            if (categoryFilter !== 'all') {
                categoryMatch = category === categoryFilter;
            }

            return scoreMatch && junkMatch && categoryMatch;
        });

        initializeDataTable(filteredData); // Re-initialize table with filtered data
    }


    // Fetch data and initialize
    // Assumes graded_leads.json is in the 'public' folder relative to index.html
    fetch('/public/graded_leads.json') // Use absolute path from server root (frontend dir) - Correct for Vercel/http-server
        .then(response => {
            if (!response.ok) {
                // Provide more context in the error message
                console.error(`Failed to fetch graded_leads.json. Status: ${response.status} ${response.statusText}`);
                // Check if the file exists or if there's a network issue.
                // Ensure the python script successfully saved graded_leads.json to frontend/public/.
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            allLeadsData = data; // Store all data
            populateCategoryFilter(allLeadsData); // Populate the category dropdown
            applyFilters(); // Apply initial filters and populate table
        })
        .catch(error => {
            console.error('Error fetching or processing leads data:', error);
            $('#leadsTable tbody').html('<tr><td colspan="8">Error loading leads data. Is graded_leads.json available in the public directory?</td></tr>');
        });

    // Event listener for the filter button
    $('#apply-filters').on('click', applyFilters);

});
