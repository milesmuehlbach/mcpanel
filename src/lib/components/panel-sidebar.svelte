<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import ServerSelector from '$lib/components/serverselection.svelte';
</script>

<Sidebar.Root>
	<Sidebar.Header>
		<h1 class="left-5 text-2xl font-extrabold">McPanel</h1>
		<ServerSelector servertitles={['Server 1']} iconpath={['/favicon.png']} />
	</Sidebar.Header>
	<Sidebar.Content>
		<Sidebar.Group />
		<Sidebar.Group />
	</Sidebar.Content>
	<Sidebar.Footer />
</Sidebar.Root>
