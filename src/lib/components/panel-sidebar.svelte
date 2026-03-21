<script lang="ts">
	import * as Sidebar from "$lib/components/ui/sidebar/index.js";
	import ServerSelector from '$lib/components/serverselection.svelte';
</script>

<Sidebar.Root>
	<Sidebar.Header>
		<h1 class="font-extrabold text-2xl left-5">McPanel</h1>
		<ServerSelector />
	</Sidebar.Header>
	<Sidebar.Content>
		<Sidebar.Group />
		<Sidebar.Group />
	</Sidebar.Content>
	<Sidebar.Footer />
</Sidebar.Root>