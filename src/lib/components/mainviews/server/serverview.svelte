<script lang="ts">
	import NoServer from '$lib/components/mainviews/server/components/noserver.svelte';
	import AppSidebar from '$lib/components/mainviews/server/components/panel-sidebar.svelte';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';

	let { newServer = () => {} }: { newServer?: () => void } = $props();

</script>

<Sidebar.Provider>
	<AppSidebar {newServer} />
	<Sidebar.Inset>
		<NoServer {newServer} />
	</Sidebar.Inset>
</Sidebar.Provider>
