<script lang="ts">
	import * as Sidebar from "$lib/components/ui/sidebar/index.js";
	import AppSidebar from '$lib/components/panel-sidebar.svelte';
</script>

<Sidebar.Provider>
	<AppSidebar />
	<Sidebar.Trigger />
</Sidebar.Provider>