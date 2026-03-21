<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import AppSidebar from '$lib/components/panel-sidebar.svelte';
	import NoServer from '$lib/components/noserver.svelte';
</script>

<Sidebar.Provider>
	<AppSidebar />
	<Sidebar.Inset>
		<NoServer />
	</Sidebar.Inset>
</Sidebar.Provider>
