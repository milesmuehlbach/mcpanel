<script>
	import NoServer from '$lib/components/mainviews/server/components/noserver.svelte';
	import AppSidebar from '$lib/components/mainviews/server/components/panel-sidebar.svelte';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
</script>

<Sidebar.Provider>
	<AppSidebar />
	<Sidebar.Inset>
		<NoServer />
	</Sidebar.Inset>
</Sidebar.Provider>
