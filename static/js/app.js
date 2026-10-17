const { createApp, ref, computed, onMounted } = Vue;

const app = createApp({
  setup() {
    // Core Data State
    const domains = ref([]);
    const allTopics = ref([]);
    const allResources = ref([]);
    const selectedDomainId = ref(null);
    const searchQuery = ref('');
    const searchResults = ref({ domains: [], topics: [], resources: [], total_matches: 0 });
    const resourceTypeFilter = ref('all');
    const onlyFavorites = ref(false);
    const siteTitle = ref("Shubh's Career Knowledge Hub");
    const isAuthenticated = ref(true);

    // Active Modals & Viewers
    const activeYouTubeResource = ref(null);
    const activePdfResource = ref(null);
    const activeNoteResource = ref(null);

    const showResourceModal = ref(false);
    const editingResource = ref(null);
    const resourceModalMode = ref('bulk'); // 'bulk' or 'single'
    const bulkDomainId = ref(null);
    const bulkTopicId = ref(null);
    const bulkType = ref('youtube');
    const bulkLinksText = ref('');
    const isSubmittingBulk = ref(false);

    const showTopicModal = ref(false);
    const editingTopic = ref(null);

    const showDomainModal = ref(false);
    const editingDomain = ref(null);

    const showBackupModal = ref(false);
    const importMode = ref('replace');
    const backupFileInput = ref(null);
    const backupMessage = ref(null);

    const showSettingsModal = ref(false);
    const siteTitleInput = ref('');
    const loginPassword = ref('');
    const settingsMessage = ref(null);
    const passwordForm = ref({ current: '', new: '' });

    // Forms
    const resourceForm = ref({
      topic_id: null,
      type: 'youtube',
      title: '',
      url: '',
      file_path: '',
      notes: '',
      tagsInput: '',
      is_favorite: false,
    });
    const uploadStatus = ref('');
    const pdfFileInput = ref(null);

    const topicForm = ref({
      domain_id: null,
      title: '',
      summary: '',
      status: 'in_progress',
      importance: 'high',
      drive_folder_url: '',
    });

    const domainForm = ref({
      name: '',
      description: '',
      color: 'purple',
      icon: 'cpu',
    });

    // Helper: API request with credentials
    const api = async (endpoint, options = {}) => {
      options.credentials = 'same-origin';
      if (!options.headers) options.headers = {};
      if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
        options.headers['Content-Type'] = 'application/json';
        options.body = JSON.stringify(options.body);
      }
      const response = await fetch(endpoint, options);
      if (response.status === 401) {
        isAuthenticated.value = false;
      }
      return response;
    };

    // Load initial data
    const fetchAllData = async () => {
      try {
        const [authRes, domainsRes, topicsRes, resourcesRes] = await Promise.all([
          api('/api/auth/status'),
          api('/api/domains'),
          api('/api/topics'),
          api('/api/resources'),
        ]);

        if (authRes.ok) {
          const authData = await authRes.json();
          isAuthenticated.value = authData.authenticated;
          siteTitle.value = authData.site_title || siteTitle.value;
          siteTitleInput.value = siteTitle.value;
        }

        if (domainsRes.ok) domains.value = await domainsRes.json();
        if (topicsRes.ok) allTopics.value = await topicsRes.json();
        if (resourcesRes.ok) allResources.value = await resourcesRes.json();
      } catch (err) {
        console.error('Failed to fetch data:', err);
      }
    };

    onMounted(() => {
      fetchAllData();
    });

    // Computed Stats & Filtering
    const totalTopics = computed(() => allTopics.value.length);
    const totalResources = computed(() => allResources.value.length);
    const masteredTopicsCount = computed(() => {
      return allTopics.value.filter(t => t.status === 'mastered').length;
    });

    const domainTopics = computed(() => {
      if (!bulkDomainId.value) return [];
      return allTopics.value.filter(t => t.domain_id === bulkDomainId.value);
    });

    const selectedBulkDomainName = computed(() => {
      const d = domains.value.find(x => x.id === bulkDomainId.value);
      return d ? d.name : '';
    });

    const bulkLinksCount = computed(() => {
      if (!bulkLinksText.value) return 0;
      return bulkLinksText.value
        .split('\n')
        .map(l => l.trim())
        .filter(l => l.length > 0).length;
    });

    const filteredTopics = computed(() => {
      let list = allTopics.value;

      // Filter by domain
      if (selectedDomainId.value !== null) {
        list = list.filter(t => t.domain_id === selectedDomainId.value);
      }

      // Filter by search query if present
      if (searchQuery.value.trim()) {
        const q = searchQuery.value.toLowerCase().trim();
        list = list.filter(t => {
          const inTitle = t.title.toLowerCase().includes(q);
          const inSummary = (t.summary || '').toLowerCase().includes(q);
          const hasMatchingResource = allResources.value.some(r => 
            r.topic_id === t.id && (
              r.title.toLowerCase().includes(q) ||
              (r.notes || '').toLowerCase().includes(q) ||
              (r.tags || []).some(tag => tag.toLowerCase().includes(q))
            )
          );
          return inTitle || inSummary || hasMatchingResource;
        });
      }

      // Filter by Resource Type or Favorites if selected
      if (resourceTypeFilter.value !== 'all' || onlyFavorites.value) {
        list = list.filter(t => {
          const resList = getTopicResources(t.id);
          return resList.length > 0;
        });
      }

      return list;
    });

    const getTopicResources = (topicId) => {
      return allResources.value.filter(r => {
        if (r.topic_id !== topicId) return false;
        if (resourceTypeFilter.value !== 'all' && r.type !== resourceTypeFilter.value) return false;
        if (onlyFavorites.value && !r.is_favorite) return false;
        if (searchQuery.value.trim()) {
          const q = searchQuery.value.toLowerCase().trim();
          const inRes = r.title.toLowerCase().includes(q) ||
                        (r.notes || '').toLowerCase().includes(q) ||
                        (r.tags || []).some(tag => tag.toLowerCase().includes(q));
          if (!inRes) return false;
        }
        return true;
      });
    };

    const selectDomain = (domainId) => {
      selectedDomainId.value = domainId;
    };

    const resetFilters = () => {
      selectedDomainId.value = null;
      searchQuery.value = '';
      resourceTypeFilter.value = 'all';
      onlyFavorites.value = false;
    };

    // Global Search Handling
    let searchTimeout = null;
    const handleSearchInput = () => {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
        performSearch();
      }, 300);
    };

    const performSearch = async () => {
      const q = searchQuery.value.trim();
      if (!q) {
        searchResults.value = { domains: [], topics: [], resources: [], total_matches: 0 };
        return;
      }
      try {
        const res = await api(`/api/search?q=${encodeURIComponent(q)}`);
        if (res.ok) {
          searchResults.value = await res.json();
        }
      } catch (err) {
        console.error('Search failed:', err);
      }
    };

    // YouTube Helpers
    const getYouTubeId = (url) => {
      if (!url) return null;
      const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|&v=)([^#&?]*).*/;
      const match = url.match(regExp);
      return match && match[2].length === 11 ? match[2] : null;
    };

    const openYouTubeModal = (res) => {
      activeYouTubeResource.value = res;
    };

    const openPdfModal = (res) => {
      activePdfResource.value = res;
    };

    const openNoteModal = (res) => {
      activeNoteResource.value = res;
    };

    const getBulkPlaceholder = (type) => {
      if (type === 'youtube') {
        return 'Paste YouTube video links here, one per line:\nhttps://www.youtube.com/watch?v=...\nhttps://youtu.be/...\nhttps://www.youtube.com/watch?v=... | Optional Custom Title';
      } else if (type === 'pdf') {
        return 'Paste PDF links here, one per line:\nhttps://arxiv.org/pdf/1706.03762.pdf\nhttps://example.com/guide.pdf';
      } else if (type === 'drive_folder' || type === 'drive_file') {
        return 'Paste Google Drive links here, one per line:\nhttps://drive.google.com/drive/folders/...\nhttps://drive.google.com/file/d/...';
      } else if (type === 'github') {
        return 'Paste GitHub repository links here, one per line:\nhttps://github.com/fastapi/fastapi\nhttps://github.com/vuejs/core';
      } else {
        return 'Paste links here, one per line:\nhttps://...\nhttps://... | Custom Title';
      }
    };

    // Resource CRUD
    const openAddResourceModal = (topic = null, resource = null) => {
      editingResource.value = resource;
      uploadStatus.value = '';
      if (resource) {
        resourceModalMode.value = 'single';
        resourceForm.value = {
          topic_id: resource.topic_id,
          type: resource.type,
          title: resource.title,
          url: resource.url || '',
          file_path: resource.file_path || '',
          notes: resource.notes || '',
          tagsInput: (resource.tags || []).join(', '),
          is_favorite: Boolean(resource.is_favorite),
        };
      } else {
        resourceModalMode.value = 'bulk';
        bulkLinksText.value = '';
        const defaultDomId = topic
          ? topic.domain_id
          : (selectedDomainId.value || (domains.value[0] ? domains.value[0].id : null));
        bulkDomainId.value = defaultDomId;
        bulkTopicId.value = topic ? topic.id : null;
        bulkType.value = 'youtube';

        resourceForm.value = {
          topic_id: topic ? topic.id : (allTopics.value[0] ? allTopics.value[0].id : null),
          type: 'youtube',
          title: '',
          url: '',
          file_path: '',
          notes: '',
          tagsInput: '',
          is_favorite: false,
        };
      }
      showResourceModal.value = true;
    };

    const submitBulkResources = async () => {
      if (!bulkDomainId.value || bulkLinksCount.value === 0) return;
      isSubmittingBulk.value = true;
      try {
        const res = await api('/api/resources/bulk', {
          method: 'POST',
          body: {
            domain_id: bulkDomainId.value,
            topic_id: bulkTopicId.value,
            type: bulkType.value,
            links_text: bulkLinksText.value,
          },
        });

        if (res.ok) {
          const [rRes, tRes, dRes] = await Promise.all([
            api('/api/resources'),
            api('/api/topics'),
            api('/api/domains'),
          ]);
          if (rRes.ok) allResources.value = await rRes.json();
          if (tRes.ok) allTopics.value = await tRes.json();
          if (dRes.ok) domains.value = await dRes.json();

          selectedDomainId.value = bulkDomainId.value;
          bulkLinksText.value = '';
          showResourceModal.value = false;
        } else {
          const err = await res.json();
          alert('Failed to add links: ' + (err.detail || 'Unknown error'));
        }
      } catch (err) {
        alert('Error adding resources: ' + err.message);
      } finally {
        isSubmittingBulk.value = false;
      }
    };

    const handleFileUpload = async (e) => {
      const file = e.target.files[0];
      if (!file) return;

      uploadStatus.value = 'Uploading file...';
      const formData = new FormData();
      formData.append('file', file);

      try {
        const res = await fetch('/api/uploads', {
          method: 'POST',
          body: formData,
          credentials: 'same-origin',
        });
        if (!res.ok) {
          const err = await res.json();
          uploadStatus.value = `Error: ${err.detail || 'Upload failed'}`;
          return;
        }
        const data = await res.json();
        resourceForm.value.url = data.url;
        resourceForm.value.file_path = data.file_path;
        if (!resourceForm.value.title) {
          resourceForm.value.title = data.original_name.replace(/\.[^/.]+$/, '');
        }
        uploadStatus.value = `✓ Uploaded: ${data.original_name}`;
      } catch (err) {
        uploadStatus.value = 'Upload error: ' + err.message;
      }
    };

    const saveResource = async () => {
      const tags = resourceForm.value.tagsInput
        .split(',')
        .map(t => t.trim())
        .filter(t => t.length > 0);

      const payload = {
        topic_id: resourceForm.value.topic_id,
        type: resourceForm.value.type,
        title: resourceForm.value.title,
        url: resourceForm.value.url,
        file_path: resourceForm.value.file_path,
        notes: resourceForm.value.notes,
        tags: tags,
        is_favorite: resourceForm.value.is_favorite,
      };

      try {
        if (editingResource.value) {
          const res = await api(`/api/resources/${editingResource.value.id}`, {
            method: 'PUT',
            body: payload,
          });
          if (res.ok) {
            const updated = await res.json();
            const idx = allResources.value.findIndex(r => r.id === updated.id);
            if (idx !== -1) allResources.value[idx] = updated;
            if (activeYouTubeResource.value && activeYouTubeResource.value.id === updated.id) {
              activeYouTubeResource.value = updated;
            }
          }
        } else {
          const res = await api('/api/resources', {
            method: 'POST',
            body: payload,
          });
          if (res.ok) {
            const created = await res.json();
            allResources.value.unshift(created);
            // Refresh domains to update count
            const dRes = await api('/api/domains');
            if (dRes.ok) domains.value = await dRes.json();
          }
        }
        showResourceModal.value = false;
      } catch (err) {
        alert('Failed to save resource: ' + err.message);
      }
    };

    const toggleFavorite = async (resource) => {
      try {
        const res = await api(`/api/resources/${resource.id}/toggle-favorite`, {
          method: 'POST',
        });
        if (res.ok) {
          const data = await res.json();
          resource.is_favorite = data.is_favorite;
        }
      } catch (err) {
        console.error('Toggle favorite failed:', err);
      }
    };

    const deleteResource = async (resource) => {
      if (!confirm(`Delete resource "${resource.title}"?`)) return;
      try {
        const res = await api(`/api/resources/${resource.id}`, { method: 'DELETE' });
        if (res.ok) {
          allResources.value = allResources.value.filter(r => r.id !== resource.id);
          const dRes = await api('/api/domains');
          if (dRes.ok) domains.value = await dRes.json();
        }
      } catch (err) {
        alert('Failed to delete resource');
      }
    };

    // Topic CRUD
    const openTopicModal = (topic = null) => {
      editingTopic.value = topic;
      if (topic) {
        topicForm.value = {
          domain_id: topic.domain_id,
          title: topic.title,
          summary: topic.summary || '',
          status: topic.status || 'in_progress',
          importance: topic.importance || 'high',
          drive_folder_url: topic.drive_folder_url || '',
        };
      } else {
        topicForm.value = {
          domain_id: selectedDomainId.value || (domains.value[0] ? domains.value[0].id : null),
          title: '',
          summary: '',
          status: 'in_progress',
          importance: 'high',
          drive_folder_url: '',
        };
      }
      showTopicModal.value = true;
    };

    const saveTopic = async () => {
      const payload = { ...topicForm.value };
      try {
        if (editingTopic.value) {
          const res = await api(`/api/topics/${editingTopic.value.id}`, {
            method: 'PUT',
            body: payload,
          });
          if (res.ok) {
            const updated = await res.json();
            const idx = allTopics.value.findIndex(t => t.id === updated.id);
            if (idx !== -1) allTopics.value[idx] = updated;
          }
        } else {
          const res = await api('/api/topics', {
            method: 'POST',
            body: payload,
          });
          if (res.ok) {
            const created = await res.json();
            allTopics.value.push(created);
            const dRes = await api('/api/domains');
            if (dRes.ok) domains.value = await dRes.json();
          }
        }
        showTopicModal.value = false;
      } catch (err) {
        alert('Failed to save topic: ' + err.message);
      }
    };

    const deleteTopic = async (topic) => {
      if (!confirm(`Delete topic "${topic.title}" and all its attached resources?`)) return;
      try {
        const res = await api(`/api/topics/${topic.id}`, { method: 'DELETE' });
        if (res.ok) {
          allTopics.value = allTopics.value.filter(t => t.id !== topic.id);
          allResources.value = allResources.value.filter(r => r.topic_id !== topic.id);
          showTopicModal.value = false;
          const dRes = await api('/api/domains');
          if (dRes.ok) domains.value = await dRes.json();
        }
      } catch (err) {
        alert('Failed to delete topic');
      }
    };

    // Domain CRUD
    const openDomainModal = (domain = null) => {
      editingDomain.value = domain;
      if (domain) {
        domainForm.value = {
          name: domain.name,
          description: domain.description || '',
          color: domain.color || 'purple',
          icon: domain.icon || 'cpu',
        };
      } else {
        domainForm.value = {
          name: '',
          description: '',
          color: 'purple',
          icon: 'cpu',
        };
      }
      showDomainModal.value = true;
    };

    const saveDomain = async () => {
      const payload = { ...domainForm.value };
      try {
        if (editingDomain.value) {
          const res = await api(`/api/domains/${editingDomain.value.id}`, {
            method: 'PUT',
            body: payload,
          });
          if (res.ok) {
            const updated = await res.json();
            const idx = domains.value.findIndex(d => d.id === updated.id);
            if (idx !== -1) domains.value[idx] = updated;
          }
        } else {
          const res = await api('/api/domains', {
            method: 'POST',
            body: payload,
          });
          if (res.ok) {
            const created = await res.json();
            domains.value.push(created);
          }
        }
        showDomainModal.value = false;
      } catch (err) {
        alert('Failed to save domain: ' + err.message);
      }
    };

    const deleteDomain = async (domain) => {
      if (!confirm(`Delete domain "${domain.name}" and all its topics and resources?`)) return;
      try {
        const res = await api(`/api/domains/${domain.id}`, { method: 'DELETE' });
        if (res.ok) {
          domains.value = domains.value.filter(d => d.id !== domain.id);
          allTopics.value = allTopics.value.filter(t => t.domain_id !== domain.id);
          if (selectedDomainId.value === domain.id) selectedDomainId.value = null;
          showDomainModal.value = false;
        }
      } catch (err) {
        alert('Failed to delete domain');
      }
    };

    // Backup & Restore
    const triggerBackupImport = async () => {
      const file = backupFileInput.value?.files[0];
      if (!file) {
        backupMessage.value = { type: 'error', text: 'Please select a JSON backup file first.' };
        return;
      }

      try {
        const text = await file.text();
        const json = JSON.parse(text);
        json.mode = importMode.value;

        const res = await api('/api/backup/import', {
          method: 'POST',
          body: json,
        });

        if (res.ok) {
          backupMessage.value = { type: 'success', text: 'Backup imported successfully! Reloading data...' };
          setTimeout(() => {
            showBackupModal.value = false;
            backupMessage.value = null;
            fetchAllData();
          }, 1200);
        } else {
          const err = await res.json();
          backupMessage.value = { type: 'error', text: 'Import failed: ' + (err.detail || 'Invalid backup') };
        }
      } catch (err) {
        backupMessage.value = { type: 'error', text: 'Failed to read file: ' + err.message };
      }
    };

    // Settings & Password Management
    const openSettingsModal = () => {
      settingsMessage.value = null;
      passwordForm.value = { current: '', new: '' };
      showSettingsModal.value = true;
    };

    const saveSiteTitle = async () => {
      if (!siteTitleInput.value.trim()) return;
      try {
        const res = await api('/api/auth/settings', {
          method: 'PUT',
          body: { site_title: siteTitleInput.value.trim() },
        });
        if (res.ok) {
          siteTitle.value = siteTitleInput.value.trim();
          settingsMessage.value = { type: 'success', text: 'Site title updated!' };
        }
      } catch (err) {
        settingsMessage.value = { type: 'error', text: 'Failed to update title' };
      }
    };

    const updateMasterPassword = async () => {
      if (!passwordForm.value.current || !passwordForm.value.new) {
        settingsMessage.value = { type: 'error', text: 'Please fill both current and new password fields' };
        return;
      }
      try {
        const res = await api('/api/auth/change-password', {
          method: 'POST',
          body: {
            current_password: passwordForm.value.current,
            new_password: passwordForm.value.new,
          },
        });
        if (res.ok) {
          settingsMessage.value = { type: 'success', text: 'Master password updated successfully!' };
          passwordForm.value = { current: '', new: '' };
        } else {
          const err = await res.json();
          settingsMessage.value = { type: 'error', text: err.detail || 'Failed to update password' };
        }
      } catch (err) {
        settingsMessage.value = { type: 'error', text: 'Error updating password: ' + err.message };
      }
    };

    const doLogin = async () => {
      try {
        const res = await api('/api/auth/login', {
          method: 'POST',
          body: { password: loginPassword.value },
        });
        if (res.ok) {
          isAuthenticated.value = true;
          loginPassword.value = '';
          settingsMessage.value = { type: 'success', text: 'Unlocked successfully!' };
          fetchAllData();
        } else {
          settingsMessage.value = { type: 'error', text: 'Incorrect password' };
        }
      } catch (err) {
        settingsMessage.value = { type: 'error', text: 'Login error' };
      }
    };

    // UI Formatting Utilities
    const renderMarkdown = (text) => {
      if (!text) return '';
      try {
        return marked.parse(text);
      } catch (e) {
        return text;
      }
    };

    const formatStatus = (st) => {
      const map = {
        mastered: '✓ Mastered',
        in_progress: '● In Progress',
        reference: '📁 Reference Archive',
        not_started: '○ To Learn Next',
      };
      return map[st] || st;
    };

    const getStatusBadgeClass = (st) => {
      const map = {
        mastered: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30',
        in_progress: 'bg-amber-500/10 text-amber-400 border border-amber-500/30',
        reference: 'bg-blue-500/10 text-blue-400 border border-blue-500/30',
        not_started: 'bg-slate-800 text-slate-400 border border-slate-700',
      };
      return map[st] || 'bg-slate-800 text-slate-400';
    };

    const getDomainColorBadge = (color) => {
      const map = {
        purple: 'bg-purple-600/20 text-purple-400',
        blue: 'bg-blue-600/20 text-blue-400',
        emerald: 'bg-emerald-600/20 text-emerald-400',
        amber: 'bg-amber-600/20 text-amber-400',
        cyan: 'bg-cyan-600/20 text-cyan-400',
        rose: 'bg-rose-600/20 text-rose-400',
      };
      return map[color] || 'bg-indigo-600/20 text-indigo-400';
    };

    const getDomainIconEmoji = (icon) => {
      const map = {
        cpu: '🧠',
        layers: '🏗️',
        server: '⚙️',
        layout: '🎨',
        cloud: '☁️',
        award: '🎯',
        folder: '📁',
      };
      return map[icon] || '📁';
    };

    const getResourceTypeIcon = (type) => {
      const map = {
        youtube: '▶',
        pdf: '📄',
        drive_folder: '📁',
        drive_file: '📄',
        note: '📝',
        article: '🌐',
        github: '💻',
      };
      return map[type] || '🔗';
    };

    const getResourceTypeBadgeClass = (type) => {
      const map = {
        youtube: 'bg-red-500/20 text-red-400',
        pdf: 'bg-rose-500/20 text-rose-400',
        drive_folder: 'bg-emerald-500/20 text-emerald-400',
        drive_file: 'bg-emerald-500/20 text-emerald-400',
        note: 'bg-purple-500/20 text-purple-400',
        article: 'bg-blue-500/20 text-blue-400',
        github: 'bg-slate-800 text-slate-200',
      };
      return map[type] || 'bg-slate-800 text-slate-400';
    };

    const formatTypeLabel = (type) => {
      const map = {
        youtube: 'YouTube',
        pdf: 'PDF',
        drive_folder: 'Drive Folder',
        drive_file: 'Drive File',
        note: 'Note',
        article: 'Article',
      };
      return map[type] || type;
    };

    return {
      domains,
      allTopics,
      allResources,
      selectedDomainId,
      searchQuery,
      searchResults,
      resourceTypeFilter,
      onlyFavorites,
      siteTitle,
      isAuthenticated,
      activeYouTubeResource,
      activePdfResource,
      activeNoteResource,
      showResourceModal,
      editingResource,
      resourceModalMode,
      bulkDomainId,
      bulkTopicId,
      bulkType,
      bulkLinksText,
      isSubmittingBulk,
      domainTopics,
      selectedBulkDomainName,
      bulkLinksCount,
      getBulkPlaceholder,
      submitBulkResources,
      showTopicModal,
      editingTopic,
      showDomainModal,
      editingDomain,
      showBackupModal,
      importMode,
      backupFileInput,
      backupMessage,
      showSettingsModal,
      siteTitleInput,
      loginPassword,
      settingsMessage,
      passwordForm,
      resourceForm,
      uploadStatus,
      pdfFileInput,
      topicForm,
      domainForm,
      totalTopics,
      totalResources,
      masteredTopicsCount,
      filteredTopics,
      getTopicResources,
      selectDomain,
      resetFilters,
      handleSearchInput,
      performSearch,
      getYouTubeId,
      openYouTubeModal,
      openPdfModal,
      openNoteModal,
      openAddResourceModal,
      handleFileUpload,
      saveResource,
      toggleFavorite,
      deleteResource,
      openTopicModal,
      saveTopic,
      deleteTopic,
      openDomainModal,
      saveDomain,
      deleteDomain,
      triggerBackupImport,
      openSettingsModal,
      saveSiteTitle,
      updateMasterPassword,
      doLogin,
      renderMarkdown,
      formatStatus,
      getStatusBadgeClass,
      getDomainColorBadge,
      getDomainIconEmoji,
      getResourceTypeIcon,
      getResourceTypeBadgeClass,
      formatTypeLabel,
    };
  }
});

app.mount('#app');
