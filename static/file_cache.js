/**
 * File caching system for offline reliability
 * Stores file metadata and results in browser storage for offline access
 */

class FileCache {
    constructor() {
        this.storageKey = 'mutation_file_cache';
        this.maxCacheSize = 50; // Maximum files to cache
        this.cacheVersion = '1.0';
    }

    /**
     * Store file data in cache for offline access
     */
    cacheFileData(fileId, fileData) {
        try {
            const cache = this.getCache();
            
            // Add timestamp for cache management
            const cacheEntry = {
                ...fileData,
                cached_at: Date.now(),
                cache_version: this.cacheVersion
            };
            
            cache[fileId] = cacheEntry;
            
            // Manage cache size
            this.manageCacheSize(cache);
            
            localStorage.setItem(this.storageKey, JSON.stringify(cache));
            console.log(`Cached file data for: ${fileId}`);
            return true;
        } catch (error) {
            console.error('Failed to cache file data:', error);
            return false;
        }
    }

    /**
     * Retrieve file data from cache
     */
    getCachedFileData(fileId) {
        try {
            const cache = this.getCache();
            const cachedData = cache[fileId];
            
            if (cachedData && this.isCacheValid(cachedData)) {
                console.log(`Retrieved cached data for: ${fileId}`);
                return cachedData;
            }
            
            return null;
        } catch (error) {
            console.error('Failed to retrieve cached data:', error);
            return null;
        }
    }

    /**
     * Check if cached data is still valid
     */
    isCacheValid(cachedData) {
        const maxAge = 24 * 60 * 60 * 1000; // 24 hours
        const age = Date.now() - cachedData.cached_at;
        
        return age < maxAge && cachedData.cache_version === this.cacheVersion;
    }

    /**
     * Get all cached data
     */
    getCache() {
        try {
            const cached = localStorage.getItem(this.storageKey);
            return cached ? JSON.parse(cached) : {};
        } catch (error) {
            console.error('Failed to parse cache:', error);
            return {};
        }
    }

    /**
     * Manage cache size by removing oldest entries
     */
    manageCacheSize(cache) {
        const entries = Object.entries(cache);
        
        if (entries.length > this.maxCacheSize) {
            // Sort by cached_at timestamp (oldest first)
            entries.sort((a, b) => a[1].cached_at - b[1].cached_at);
            
            // Remove oldest entries
            const toRemove = entries.length - this.maxCacheSize;
            for (let i = 0; i < toRemove; i++) {
                delete cache[entries[i][0]];
            }
        }
    }

    /**
     * Clear all cached data
     */
    clearCache() {
        try {
            localStorage.removeItem(this.storageKey);
            console.log('Cache cleared');
            return true;
        } catch (error) {
            console.error('Failed to clear cache:', error);
            return false;
        }
    }

    /**
     * Get cache statistics
     */
    getCacheStats() {
        const cache = this.getCache();
        const entries = Object.entries(cache);
        const validEntries = entries.filter(([_, data]) => this.isCacheValid(data));
        
        return {
            total: entries.length,
            valid: validEntries.length,
            expired: entries.length - validEntries.length,
            size: JSON.stringify(cache).length
        };
    }

    /**
     * Check if browser supports offline storage
     */
    isSupported() {
        try {
            const testKey = '__cache_test__';
            localStorage.setItem(testKey, 'test');
            localStorage.removeItem(testKey);
            return true;
        } catch (error) {
            return false;
        }
    }
}

// Export for use in other modules
window.FileCache = FileCache;