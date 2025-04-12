import React, { useState, useEffect, useMemo } from 'react';
import { X, Filter, Download, Inbox, RefreshCw, Calendar, Clock, Phone, Tag, CheckCircle, CircleAlert, BarChart3, Settings, Search } from 'lucide-react';

// Define the Lead interface to match your JSON structure
interface Lead {
  id: number;
  scraped: string;
  datePosted: string;
  city: string | null;
  title: string;
  url: string;
  description: string;
  value: string | null;
  contactMethod: string;
  category: string;
  contacted: "Yes" | "No";
  followUp: string | null;
  aiScore: string;
  isJunk: string;
  aiReason: string;
}

// Category map for readable names and colors
const categoryMap: Record<string, { label: string; color: string }> = {
  "web": { label: "Web Development", color: "bg-blue-100 text-blue-800" },
  "cpg": { label: "Computer Gigs", color: "bg-purple-100 text-purple-800" },
  "wri": { label: "Writing", color: "bg-green-100 text-green-800" },
  "crg": { label: "Creative Gigs", color: "bg-yellow-100 text-yellow-800" },
  "mar": { label: "Marketing", color: "bg-red-100 text-red-800" }
};

// Custom hook for managing filters
const useFilters = (leads: Lead[]) => {
  const [searchTerm, setSearchTerm] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string[]>([]);
  const [cityFilter, setCityFilter] = useState<string[]>([]);
  const [dateFilter, setDateFilter] = useState<{ start: string | null; end: string | null }>({ start: null, end: null });
  const [contactedFilter, setContactedFilter] = useState<string | null>(null);

  // Get all unique cities for filter options
  const cities = useMemo(() => {
    return [...new Set(leads.map(lead => lead.city).filter(city => city))] as string[];
  }, [leads]);

  // Filter leads based on all criteria
  const filteredLeads = useMemo(() => {
    return leads.filter(lead => {
      // Search term filter
      const searchMatch =
        searchTerm === "" ||
        lead.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        lead.description.toLowerCase().includes(searchTerm.toLowerCase());

      // Category filter
      const categoryMatch =
        categoryFilter.length === 0 ||
        categoryFilter.includes(lead.category);

      // City filter
      const cityMatch =
        cityFilter.length === 0 ||
        (lead.city && cityFilter.includes(lead.city));

      // Date filter
      let dateMatch = true; // Default to true if dates are invalid/missing
      try {
          const postedDate = lead.datePosted ? new Date(lead.datePosted) : null;
          const startDate = dateFilter.start ? new Date(dateFilter.start) : null;
          const endDate = dateFilter.end ? new Date(dateFilter.end) : null;

          if (postedDate && !isNaN(postedDate.getTime())) { // Check if postedDate is valid
              const isStartDateValid = startDate && !isNaN(startDate.getTime());
              const isEndDateValid = endDate && !isNaN(endDate.getTime());
              dateMatch =
                  (!isStartDateValid || postedDate >= startDate!) &&
                  (!isEndDateValid || postedDate <= endDate!);
          } else if (dateFilter.start || dateFilter.end) {
              // If a filter is set but the lead date is invalid/missing, exclude it
              dateMatch = false;
          }
      } catch (e) {
          console.error("Error parsing date for filtering:", lead.datePosted, e);
          dateMatch = false; // Exclude on error
      }


      // Contacted filter
      const contactedMatch =
        contactedFilter === null ||
        (contactedFilter === "Yes" && lead.contacted === "Yes") ||
        (contactedFilter === "No" && lead.contacted === "No");

      return searchMatch && categoryMatch && cityMatch && dateMatch && contactedMatch;
    });
  }, [leads, searchTerm, categoryFilter, cityFilter, dateFilter, contactedFilter]);

  return {
    searchTerm,
    setSearchTerm,
    categoryFilter,
    setCategoryFilter,
    cityFilter,
    setCityFilter,
    dateFilter,
    setDateFilter,
    contactedFilter,
    setContactedFilter,
    cities,
    filteredLeads
  };
};

const LeadsDashboard: React.FC = () => {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null); // Add missing error state
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [view, setView] = useState<"table" | "kanban" | "statistics">("table");
  const [showFilterPanel, setShowFilterPanel] = useState(false);
  const [savedFilters, setSavedFilters] = useState<Array<{id: number; name: string; config: any}>>([]);
  const [sortField, setSortField] = useState('datePosted');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  // --- Data Fetching ---
  const fetchData = async () => {
    try {
      setIsLoading(true);
      setError(null); // Reset error state before fetching
      // Add cache-busting query param
        const response = await fetch(`/graded_leads.json?t=${Date.now()}`);
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const data = await response.json();

        // Ensure data is an array before mapping
        if (!Array.isArray(data)) {
             console.error("Fetched data is not an array:", data);
             throw new Error("Invalid data format received from server.");
        }

        // Ensure data is in the correct format with proper type casting for enums
        const formattedData = data.map((item: any) => ({
          ...item,
          // Ensure required fields have fallbacks if potentially missing in JSON
          id: item.id ?? Math.random(), // Provide a fallback ID if null/undefined
          scraped: item.scraped ?? "N/A",
          datePosted: item.datePosted ?? "N/A",
          title: item.title ?? "Untitled Lead",
          url: item.url ?? "#",
          description: item.description ?? "-",
          contactMethod: item.contactMethod ?? "N/A",
          category: item.category ?? "unknown",
          aiScore: item.aiScore ?? "N/A",
          isJunk: item.isJunk ?? "No",
          aiReason: item.aiReason ?? "N/A",
          contacted: item.contacted === "Yes" ? "Yes" : "No" as "Yes" | "No" // Cast to literal type
        }));

        setLeads(formattedData);
      } catch (error) {
        console.error("Error fetching lead data:", error);
        setError(error instanceof Error ? error.message : "An unknown error occurred while fetching data."); // Set error state
      } finally {
        setIsLoading(false);
      }
    };

  // Fetch data on component mount
  useEffect(() => {
    fetchData();
  }, []); // Empty dependency array means this runs once on mount


  const {
    searchTerm,
    setSearchTerm,
    categoryFilter,
    setCategoryFilter,
    cityFilter,
    setCityFilter,
    dateFilter,
    setDateFilter,
    contactedFilter,
    setContactedFilter,
    cities,
    filteredLeads
  } = useFilters(leads);

  // Categories from mapping
  const categories = Object.keys(categoryMap);

  // Reset all filters
  const resetFilters = () => {
    setSearchTerm("");
    setCategoryFilter([]);
    setCityFilter([]);
    setDateFilter({ start: null, end: null });
    setContactedFilter(null);
  };

  // Save current filter configuration
  const saveCurrentFilter = (name: string) => {
    const newFilter = {
      id: Date.now(),
      name,
      config: {
        searchTerm,
        categoryFilter,
        cityFilter,
        dateFilter,
        contactedFilter
      }
    };
    setSavedFilters([...savedFilters, newFilter]);
  };

  // Apply a saved filter
  const applySavedFilter = (filter: {id: number; name: string; config: any}) => {
    setSearchTerm(filter.config.searchTerm);
    setCategoryFilter(filter.config.categoryFilter);
    setCityFilter(filter.config.cityFilter);
    setDateFilter(filter.config.dateFilter);
    setContactedFilter(filter.config.contactedFilter);
  };

  // Toggle category in filter
  const toggleCategoryFilter = (category: string) => {
    setCategoryFilter(
      categoryFilter.includes(category)
        ? categoryFilter.filter(c => c !== category)
        : [...categoryFilter, category]
    );
  };

  // Toggle city in filter
  const toggleCityFilter = (city: string) => {
    setCityFilter(
      cityFilter.includes(city)
        ? cityFilter.filter(c => c !== city)
        : [...cityFilter, city]
    );
  };

  // Mark a lead as contacted
  const markAsContacted = (id: number, status: "Yes" | "No" = "Yes") => {
    setLeads(leads.map(lead =>
      lead.id === id ? { ...lead, contacted: status } : lead
    ));
     // TODO: Add persistence logic here (e.g., API call to update backend)
     console.log(`Lead ${id} marked as ${status} (local state only)`);
  };

  // Set follow up date
  const setFollowUpDate = (id: number, date: string | null) => { // Allow null date
    setLeads(leads.map(lead =>
      lead.id === id ? { ...lead, followUp: date } : lead
    ));
     // TODO: Add persistence logic here (e.g., API call to update backend)
     console.log(`Follow up for lead ${id} set to ${date} (local state only)`);
  };

  // Handle sorting
  const handleSort = (field: keyof Lead) => { // Use keyof Lead for type safety
    if (sortField === field) {
      // Toggle direction if clicking the same field
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      // New field, set it and default to descending
      setSortField(field);
      setSortDirection('desc');
    }
  };

  // Apply sorting to filteredLeads
  const sortedLeads = useMemo(() => {
    return [...filteredLeads].sort((a, b) => {
      // Cast to 'any' to allow dynamic property access, or use more specific type checks
      const fieldA = (a as any)[sortField];
      const fieldB = (b as any)[sortField];

      // Handle date fields
      if (['datePosted', 'scraped', 'followUp'].includes(sortField)) {
        // Handle null/invalid dates gracefully - treat them as earliest/latest depending on sort
        const dateA = fieldA ? new Date(fieldA as string) : (sortDirection === 'asc' ? new Date(-8640000000000000) : new Date(8640000000000000));
        const dateB = fieldB ? new Date(fieldB as string) : (sortDirection === 'asc' ? new Date(-8640000000000000) : new Date(8640000000000000));
        const timeA = !isNaN(dateA.getTime()) ? dateA.getTime() : (sortDirection === 'asc' ? -Infinity : Infinity);
        const timeB = !isNaN(dateB.getTime()) ? dateB.getTime() : (sortDirection === 'asc' ? -Infinity : Infinity);

        return sortDirection === 'asc' ? timeA - timeB : timeB - timeA;
      }

      // Handle numeric fields (like aiScore if it can be numeric)
      if (sortField === 'aiScore') {
          const numA = typeof fieldA === 'number' ? fieldA : parseFloat(fieldA as string);
          const numB = typeof fieldB === 'number' ? fieldB : parseFloat(fieldB as string);
          const valA = !isNaN(numA) ? numA : (sortDirection === 'asc' ? -Infinity : Infinity);
          const valB = !isNaN(numB) ? numB : (sortDirection === 'asc' ? -Infinity : Infinity);
          return sortDirection === 'asc' ? valA - valB : valB - valA;
      }


      // Handle text fields (case-insensitive)
      const valueA = (fieldA || '').toString().toLowerCase();
      const valueB = (fieldB || '').toString().toLowerCase();

      return sortDirection === 'asc'
        ? valueA.localeCompare(valueB)
        : valueB.localeCompare(valueA);
    });
  }, [filteredLeads, sortField, sortDirection]);

  // Simulate refreshing data - replaced by actual fetch
  // const refreshData = () => {
  //   setIsLoading(true);
  //   // Simulate API call
  //   setTimeout(() => {
  //     setIsLoading(false);
  //   }, 1000);
  // };

  // Format date for display
  const formatDate = (dateStr: string | null): string => {
    if (!dateStr || dateStr === "N/A") return "-";
    try {
      const date = new Date(dateStr);
      if (isNaN(date.getTime())) return "Invalid Date";
      return date.toLocaleDateString('en-US', { month: '2-digit', day: '2-digit', year: 'numeric' });
    } catch (e) {
      console.error("Error formatting date:", dateStr, e);
      return "Invalid Date";
    }
  };

  // View lead details
  const viewLeadDetails = (lead: Lead) => {
    setSelectedLead(lead);
  };

  // Close lead details modal
  const closeLeadDetails = () => {
    setSelectedLead(null);
  };

  // Statistics for dashboard
  const stats = useMemo(() => {
    const total = leads.length;
    const contactedCount = leads.filter(lead => lead.contacted === "Yes").length;
    const notContactedCount = total - contactedCount;
    const categoryCounts = categories.reduce((acc, cat) => {
        acc[cat] = leads.filter(lead => lead.category === cat).length;
        return acc;
    }, {} as { [key: string]: number });

    return {
      total,
      filtered: sortedLeads.length, // Use sortedLeads length for filtered count
      contacted: contactedCount,
      notContacted: notContactedCount,
      byCategory: categories.map(cat => ({
        category: cat,
        label: categoryMap[cat]?.label || cat, // Fallback label
        count: categoryCounts[cat] || 0
      }))
    };
  }, [leads, sortedLeads, categories]); // Depend on sortedLeads

  // Helper to render sort icons
  const renderSortIcon = (field: keyof Lead) => {
    if (sortField !== field) return null;
    return <span className="ml-1">{sortDirection === 'asc' ? '↑' : '↓'}</span>;
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <h1 className="text-xl font-bold text-gray-900">Craigslist Leads Dashboard</h1>
            <div className="flex items-center space-x-4">
              <p className="text-sm text-gray-500">
                Generated: {new Date().toLocaleString()}
              </p>
              <button
                onClick={fetchData} // Correct: Call the fetchData function defined in the component scope
                disabled={isLoading}
                className={`inline-flex items-center px-3 py-1 border border-transparent text-sm leading-5 font-medium rounded-md text-white ${isLoading ? 'bg-indigo-300 cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-500 focus:outline-none focus:border-indigo-700 focus:shadow-outline-indigo active:bg-indigo-700'} transition ease-in-out duration-150`}
              >
                <RefreshCw className={`w-4 h-4 mr-1 ${isLoading ? 'animate-spin' : ''}`} />
                {isLoading ? 'Refreshing...' : 'Refresh'}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Stats overview */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
           {/* Cards remain the same */}
           <div className="bg-white overflow-hidden shadow rounded-lg">
             <div className="px-4 py-5 sm:p-6">
               <div className="flex items-center">
                 <div className="flex-shrink-0 bg-indigo-500 rounded-md p-3"><Inbox className="h-6 w-6 text-white" /></div>
                 <div className="ml-5 w-0 flex-1"><dl><dt className="text-sm font-medium text-gray-500 truncate">Total Leads</dt><dd className="text-2xl font-semibold text-gray-900">{stats.total}</dd></dl></div>
               </div>
             </div>
           </div>
           <div className="bg-white overflow-hidden shadow rounded-lg">
             <div className="px-4 py-5 sm:p-6">
               <div className="flex items-center">
                 <div className="flex-shrink-0 bg-green-500 rounded-md p-3"><CheckCircle className="h-6 w-6 text-white" /></div>
                 <div className="ml-5 w-0 flex-1"><dl><dt className="text-sm font-medium text-gray-500 truncate">Contacted</dt><dd className="text-2xl font-semibold text-gray-900">{stats.contacted}</dd></dl></div>
               </div>
             </div>
           </div>
           <div className="bg-white overflow-hidden shadow rounded-lg">
             <div className="px-4 py-5 sm:p-6">
               <div className="flex items-center">
                 <div className="flex-shrink-0 bg-yellow-500 rounded-md p-3"><CircleAlert className="h-6 w-6 text-white" /></div>
                 <div className="ml-5 w-0 flex-1"><dl><dt className="text-sm font-medium text-gray-500 truncate">Not Contacted</dt><dd className="text-2xl font-semibold text-gray-900">{stats.notContacted}</dd></dl></div>
               </div>
             </div>
           </div>
           <div className="bg-white overflow-hidden shadow rounded-lg">
             <div className="px-4 py-5 sm:p-6">
               <div className="flex items-center">
                 <div className="flex-shrink-0 bg-purple-500 rounded-md p-3"><Filter className="h-6 w-6 text-white" /></div>
                 <div className="ml-5 w-0 flex-1"><dl><dt className="text-sm font-medium text-gray-500 truncate">Filtered Results</dt><dd className="text-2xl font-semibold text-gray-900">{stats.filtered}</dd></dl></div>
               </div>
             </div>
           </div>
        </div>

        {/* Controls and View Selector */}
        <div className="flex flex-col md:flex-row justify-between items-center mb-6 space-y-4 md:space-y-0">
          {/* Search Bar */}
          <div className="relative flex-grow md:max-w-md md:mr-4 w-full md:w-auto">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none"><Search className="h-5 w-5 text-gray-400" /></div>
            <input type="text" placeholder="Search by title or description..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="focus:ring-indigo-500 focus:border-indigo-500 block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 text-gray-900 sm:text-sm"/>
          </div>

          {/* View Controls */}
          <div className="flex items-center space-x-2 flex-wrap justify-center md:justify-end">
            <div className="inline-flex shadow-sm rounded-md mb-2 sm:mb-0">
              <button type="button" onClick={() => setView("table")} className={`relative inline-flex items-center px-4 py-2 rounded-l-md border border-gray-300 text-sm font-medium ${view === "table" ? "bg-indigo-600 text-white z-10" : "bg-white text-gray-700 hover:bg-gray-50"}`}>Table</button>
              <button type="button" onClick={() => setView("kanban")} className={`relative -ml-px inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium ${view === "kanban" ? "bg-indigo-600 text-white z-10" : "bg-white text-gray-700 hover:bg-gray-50"}`}>Kanban</button>
              <button type="button" onClick={() => setView("statistics")} className={`relative -ml-px inline-flex items-center px-4 py-2 rounded-r-md border border-gray-300 text-sm font-medium ${view === "statistics" ? "bg-indigo-600 text-white z-10" : "bg-white text-gray-700 hover:bg-gray-50"}`}>Statistics</button>
            </div>
            <button type="button" onClick={() => setShowFilterPanel(!showFilterPanel)} className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 mb-2 sm:mb-0"><Filter className="-ml-1 mr-2 h-5 w-5 text-gray-400" />Filters {showFilterPanel ? '(Hide)' : `(${stats.filtered})`}</button>
            <button type="button" onClick={() => alert("Export feature not implemented yet.")} className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 mb-2 sm:mb-0"><Download className="-ml-1 mr-2 h-5 w-5 text-gray-400" />Export</button>
          </div>
        </div>

        {/* Current Sort Indicator - Only show in table view */}
        {view === 'table' && (
            <div className="mb-4 text-sm text-gray-500">
              Sorted by: {sortField} ({sortDirection === 'asc' ? 'Oldest/Lowest first' : 'Newest/Highest first'})
            </div>
        )}


        {/* Filter Panel */}
        {showFilterPanel && (
          <div className="bg-white p-4 shadow rounded-lg mb-6 border border-gray-200">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-medium text-gray-900">Filters</h3>
              <button type="button" onClick={() => setShowFilterPanel(false)} className="text-gray-400 hover:text-gray-500"><X className="h-5 w-5" /></button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Category Filter */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Category</label>
                <div className="space-y-1 max-h-40 overflow-y-auto border rounded p-2">
                  {categories.map(category => (<div key={category} className="flex items-center"><input id={`category-${category}`} type="checkbox" checked={categoryFilter.includes(category)} onChange={() => toggleCategoryFilter(category)} className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"/><label htmlFor={`category-${category}`} className="ml-2 block text-sm text-gray-700">{categoryMap[category]?.label || category}</label></div>))}
                </div>
              </div>
              {/* City Filter */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">City ({cities.length})</label>
                <div className="space-y-1 max-h-40 overflow-y-auto border rounded p-2">
                  {cities.sort().map(city => (<div key={city} className="flex items-center"><input id={`city-${city}`} type="checkbox" checked={cityFilter.includes(city)} onChange={() => toggleCityFilter(city)} className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"/><label htmlFor={`city-${city}`} className="ml-2 block text-sm text-gray-700">{city}</label></div>))}
                </div>
              </div>
              {/* Date and Contacted Filter */}
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Date Posted</label>
                  <div className="grid grid-cols-2 gap-2">
                    <div><label htmlFor="date-from" className="block text-xs text-gray-500">From</label><input id="date-from" type="date" value={dateFilter.start || ""} onChange={(e) => setDateFilter({...dateFilter, start: e.target.value || null})} className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-1 px-2 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"/></div>
                    <div><label htmlFor="date-to" className="block text-xs text-gray-500">To</label><input id="date-to" type="date" value={dateFilter.end || ""} onChange={(e) => setDateFilter({...dateFilter, end: e.target.value || null})} className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-1 px-2 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"/></div>
                  </div>
                </div>
                <div>
                  <label htmlFor="contact-status" className="block text-sm font-medium text-gray-700 mb-1">Contact Status</label>
                  <select id="contact-status" value={contactedFilter || ""} onChange={(e) => setContactedFilter(e.target.value as "Yes" | "No" | null || null)} className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md">
                    <option value="">All</option><option value="Yes">Contacted</option><option value="No">Not Contacted</option>
                  </select>
                </div>
              </div>
            </div>
            <div className="mt-6 flex items-center justify-between flex-wrap gap-2">
              <button type="button" onClick={resetFilters} className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">Reset Filters</button>
              <div className="flex space-x-2 flex-wrap gap-2">
                <button type="button" onClick={() => { const name = prompt("Enter a name for this filter set:"); if (name && name.trim()) saveCurrentFilter(name.trim()); }} className="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">Save Filters</button>
                {savedFilters.length > 0 && (<select onChange={(e) => { if (e.target.value) { const filter = savedFilters.find(f => f.id === parseInt(e.target.value)); if (filter) applySavedFilter(filter); } }} className="block w-48 pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm rounded-md" defaultValue=""><option value="">Apply Saved Filter</option>{savedFilters.map(filter => (<option key={filter.id} value={filter.id}>{filter.name}</option>))}</select>)}
              </div>
            </div>
          </div>
        )}

        {/* Main content based on selected view */}
        {isLoading && (<div className="flex justify-center items-center h-64"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500"></div><p className="ml-4 text-gray-600">Loading leads...</p></div>)}
        {error && (<div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative mb-6" role="alert"><strong className="font-bold">Error:</strong><span className="block sm:inline"> Failed to load leads data. {error}</span></div>)}

        {!isLoading && !error && (
          <>
            {/* Table View */}
            {view === "table" && (
              <div className="shadow overflow-hidden border-b border-gray-200 sm:rounded-lg">
                <div className="bg-white overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer" onClick={() => handleSort('contacted')}>Status{renderSortIcon('contacted')}</th>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer" onClick={() => handleSort('title')}>Lead Details{renderSortIcon('title')}</th>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer" onClick={() => handleSort('category')}>Category{renderSortIcon('category')}</th>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer" onClick={() => handleSort('datePosted')}>Date Posted{renderSortIcon('datePosted')}</th>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer" onClick={() => handleSort('followUp')}>Follow Up{renderSortIcon('followUp')}</th>
                        <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {sortedLeads.length === 0 ? (<tr><td colSpan={6} className="px-6 py-10 text-center text-sm text-gray-500">No leads found matching the current filters.</td></tr>) : (
                        sortedLeads.map((lead) => (
                          <tr key={lead.id} className="hover:bg-gray-50">
                            <td className="px-6 py-4 whitespace-nowrap"><span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${lead.contacted === "Yes" ? "bg-green-100 text-green-800" : "bg-yellow-100 text-yellow-800"}`}>{lead.contacted}</span></td>
                            <td className="px-6 py-4"><div className="text-sm font-medium text-indigo-600 hover:text-indigo-900"><a href={lead.url} target="_blank" rel="noopener noreferrer">{lead.title}</a></div><div className="text-sm text-gray-500 max-w-md truncate" title={lead.description}>{lead.description}</div><div className="text-xs text-gray-500 mt-1">{lead.city}</div></td>
                            <td className="px-6 py-4 whitespace-nowrap"><span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${categoryMap[lead.category]?.color || 'bg-gray-100 text-gray-800'}`}>{categoryMap[lead.category]?.label || lead.category}</span></td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{formatDate(lead.datePosted)}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{lead.followUp ? formatDate(lead.followUp) : "-"}</td>
                            <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium"><button onClick={() => viewLeadDetails(lead)} className="text-indigo-600 hover:text-indigo-900 mr-3">View</button>{lead.contacted === "No" ? (<button onClick={() => markAsContacted(lead.id, "Yes")} className="text-green-600 hover:text-green-900">Mark Contacted</button>) : (<button onClick={() => markAsContacted(lead.id, "No")} className="text-yellow-600 hover:text-yellow-900">Mark Uncontacted</button>)}</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Kanban View */}
            {view === "kanban" && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Not Contacted Column */}
                <div className="bg-white shadow rounded-lg overflow-hidden">
                  <div className="px-4 py-5 border-b border-gray-200 sm:px-6"><h3 className="text-lg leading-6 font-medium text-gray-900">Not Contacted <span className="ml-2 py-0.5 px-2 bg-yellow-100 text-yellow-800 rounded-full text-xs">{sortedLeads.filter(l => l.contacted === "No").length}</span></h3></div>
                  <div className="overflow-y-auto p-4 space-y-4" style={{ maxHeight: '70vh' }}>
                    {sortedLeads.filter(lead => lead.contacted === "No").map(lead => (
                      <div key={lead.id} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer" onClick={() => viewLeadDetails(lead)}>
                        <div className="flex justify-between items-center"><span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${categoryMap[lead.category]?.color || 'bg-gray-100 text-gray-800'}`}>{categoryMap[lead.category]?.label || lead.category}</span><span className="text-xs text-gray-500">{formatDate(lead.datePosted)}</span></div>
                        <h4 className="font-medium text-gray-900 mt-2">{lead.title}</h4><p className="text-sm text-gray-500 mt-1 line-clamp-2" title={lead.description}>{lead.description}</p>
                        <div className="mt-4 flex justify-between items-center"><span className="text-xs text-gray-500">{lead.city}</span><button onClick={(e) => { e.stopPropagation(); markAsContacted(lead.id, "Yes"); }} className="inline-flex items-center px-2.5 py-1.5 border border-transparent text-xs font-medium rounded text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">Mark Contacted</button></div>
                      </div>
                    ))}
                    {sortedLeads.filter(l => l.contacted === "No").length === 0 && (<div className="text-center py-10 text-gray-500">No leads to display</div>)}
                  </div>
                </div>
                {/* Contacted Column */}
                <div className="bg-white shadow rounded-lg overflow-hidden">
                   <div className="px-4 py-5 border-b border-gray-200 sm:px-6"><h3 className="text-lg leading-6 font-medium text-gray-900">Contacted <span className="ml-2 py-0.5 px-2 bg-green-100 text-green-800 rounded-full text-xs">{sortedLeads.filter(l => l.contacted === "Yes").length}</span></h3></div>
                   <div className="overflow-y-auto p-4 space-y-4" style={{ maxHeight: '70vh' }}>
                     {sortedLeads.filter(lead => lead.contacted === "Yes").map(lead => (
                       <div key={lead.id} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer" onClick={() => viewLeadDetails(lead)}>
                         <div className="flex justify-between items-center"><span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${categoryMap[lead.category]?.color || 'bg-gray-100 text-gray-800'}`}>{categoryMap[lead.category]?.label || lead.category}</span><span className="text-xs text-gray-500">{formatDate(lead.datePosted)}</span></div>
                         <h4 className="font-medium text-gray-900 mt-2">{lead.title}</h4><p className="text-sm text-gray-500 mt-1 line-clamp-2" title={lead.description}>{lead.description}</p>
                         {lead.followUp && (<div className="mt-2 text-sm"><span className="font-medium text-gray-900">Follow up:</span> {formatDate(lead.followUp)}</div>)}
                         <div className="mt-4 flex justify-between items-center"><span className="text-xs text-gray-500">{lead.city}</span><button onClick={(e) => { e.stopPropagation(); markAsContacted(lead.id, "No"); }} className="inline-flex items-center px-2.5 py-1.5 border border-transparent text-xs font-medium rounded text-yellow-700 bg-yellow-100 hover:bg-yellow-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-yellow-500">Mark Uncontacted</button></div>
                       </div>
                     ))}
                     {sortedLeads.filter(l => l.contacted === "Yes").length === 0 && (<div className="text-center py-10 text-gray-500">No leads to display</div>)}
                   </div>
                 </div>
              </div>
            )}

            {/* Statistics View */}
            {view === "statistics" && (
              <div className="bg-white shadow rounded-lg overflow-hidden">
                <div className="px-4 py-5 border-b border-gray-200 sm:px-6"><h3 className="text-lg leading-6 font-medium text-gray-900">Lead Statistics</h3></div>
                <div className="p-6">
                  <h4 className="text-lg font-medium text-gray-900 mb-4">By Category</h4>
                  <div className="space-y-4">
                    {stats.byCategory.map(cat => (<div key={cat.category}><div className="flex items-center justify-between mb-1"><span className="text-sm font-medium text-gray-700">{cat.label}</span><span className="text-sm text-gray-700">{cat.count} leads ({stats.total > 0 ? Math.round(cat.count / stats.total * 100) : 0}%)</span></div><div className="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700"><div className="bg-indigo-600 h-2.5 rounded-full" style={{ width: `${stats.total > 0 ? (cat.count / stats.total) * 100 : 0}%` }}></div></div></div>))}
                  </div>
                  <div className="mt-8">
                    <h4 className="text-lg font-medium text-gray-900 mb-4">Contact Status</h4>
                    <div className="w-full bg-gray-200 rounded-full h-4 flex dark:bg-gray-700">
                      {stats.total > 0 && (<><div className="bg-green-500 h-4 rounded-l-full flex items-center justify-center text-xs text-white" style={{ width: `${(stats.contacted / stats.total) * 100}%` }} title={`Contacted: ${stats.contacted}`}>{stats.contacted > 0 && `${Math.round(stats.contacted / stats.total * 100)}%`}</div><div className="bg-yellow-500 h-4 rounded-r-full flex items-center justify-center text-xs text-white" style={{ width: `${(stats.notContacted / stats.total) * 100}%` }} title={`Not Contacted: ${stats.notContacted}`}>{stats.notContacted > 0 && `${Math.round(stats.notContacted / stats.total * 100)}%`}</div></>)}
                      {stats.total === 0 && (<div className="h-4 w-full bg-gray-200 rounded-full"></div>)}
                    </div>
                    <div className="flex justify-between mt-2"><div className="flex items-center"><div className="w-3 h-3 bg-green-500 rounded-full mr-2"></div><span className="text-sm text-gray-700">Contacted ({stats.contacted})</span></div><div className="flex items-center"><div className="w-3 h-3 bg-yellow-500 rounded-full mr-2"></div><span className="text-sm text-gray-700">Not Contacted ({stats.notContacted})</span></div></div>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </main>

      {/* Lead Details Modal */}
      {selectedLead && (
        <div className="fixed z-50 inset-0 overflow-y-auto">
          <div className="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
            <div className="fixed inset-0 transition-opacity" aria-hidden="true" onClick={closeLeadDetails}><div className="absolute inset-0 bg-gray-500 opacity-75"></div></div>
            <span className="hidden sm:inline-block sm:align-middle sm:h-screen" aria-hidden="true">&#8203;</span>
            <div className="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
              <div className="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
                <div className="sm:flex sm:items-start">
                  <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left w-full">
                    <h3 className="text-lg leading-6 font-medium text-gray-900 mb-4" id="modal-title">{selectedLead.title}</h3>
                    <div className="mt-2 space-y-3">
                      <div className="flex items-center justify-between"><span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${categoryMap[selectedLead.category]?.color || 'bg-gray-100 text-gray-800'}`}>{categoryMap[selectedLead.category]?.label || selectedLead.category}</span><span className="text-sm text-gray-500">Posted: {formatDate(selectedLead.datePosted)}</span></div>
                      <div className="mt-2"><p className="text-sm text-gray-600 break-words whitespace-pre-wrap">{selectedLead.description}</p></div>
                      <div className="flex justify-between text-sm"><div><span className="font-medium text-gray-900">City:</span> {selectedLead.city || "N/A"}</div><div><span className="font-medium text-gray-900">Contact Method:</span> {selectedLead.contactMethod}</div></div>
                      <div className="flex justify-between text-sm"><div><span className="font-medium text-gray-900">Contacted:</span> {selectedLead.contacted}</div><div><span className="font-medium text-gray-900">Follow Up:</span> {selectedLead.followUp ? formatDate(selectedLead.followUp) : "None"}</div></div>
                      <div className="border-t border-gray-200 pt-3 mt-3"><h4 className="text-sm font-medium text-gray-900 mb-2">AI Analysis</h4><div className="flex justify-between text-sm"><div><span className="font-medium text-gray-900">Score:</span> {selectedLead.aiScore ?? "N/A"}</div><div><span className="font-medium text-gray-900">Junk?:</span> {selectedLead.isJunk}</div></div><div className="text-sm mt-1"><span className="font-medium text-gray-900">Reason:</span> {selectedLead.aiReason || "N/A"}</div></div>
                      <div className="border-t border-gray-200 pt-4 mt-4"><h4 className="text-sm font-medium text-gray-900 mb-2">Actions</h4>
                        <div className="flex flex-col space-y-3">
                          {selectedLead.contacted === "No" ? (<button onClick={() => { markAsContacted(selectedLead.id, "Yes"); setSelectedLead({...selectedLead!, contacted: "Yes"}); }} className="inline-flex justify-center items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"><CheckCircle className="w-4 h-4 mr-2" />Mark as Contacted</button>) : (<button onClick={() => { markAsContacted(selectedLead.id, "No"); setSelectedLead({...selectedLead!, contacted: "No"}); }} className="inline-flex justify-center items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500"><CircleAlert className="w-4 h-4 mr-2" />Mark as Not Contacted</button>)}
                          <div className="flex space-x-2">
                            <div className="flex-grow"><label htmlFor={`followUpDate-${selectedLead.id}`} className="block text-xs text-gray-700 mb-1">Set Follow Up Date</label><input id={`followUpDate-${selectedLead.id}`} type="date" value={selectedLead.followUp ?? ""} onChange={(e) => { const newDate = e.target.value || null; setFollowUpDate(selectedLead!.id, newDate); setSelectedLead({...selectedLead!, followUp: newDate}); }} className="block w-full border border-gray-300 rounded-md shadow-sm py-1 px-2 sm:text-sm"/></div>
                            <div><label className="block text-xs text-gray-700 mb-1 opacity-0">Link</label><a href={selectedLead.url} target="_blank" rel="noopener noreferrer" className="inline-flex justify-center items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">View Original</a></div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div className="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse"><button type="button" onClick={closeLeadDetails} className="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-indigo-600 text-base font-medium text-white hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 sm:ml-3 sm:w-auto sm:text-sm">Close</button></div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default LeadsDashboard;
