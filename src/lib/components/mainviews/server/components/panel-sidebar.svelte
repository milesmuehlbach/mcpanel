<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar';
	import ServerSelector from '$lib/components/mainviews/server/components/serverselection.svelte';
	import SidebarFooter from '$lib/components/mainviews/server/components/sidebarfooter.svelte';

	let { newServer = () => {} }: { newServer?: () => void } = $props();

</script>

<Sidebar.Root collapsible="icon">
	<Sidebar.Header>
		<ServerSelector servertitles={['McPanel Test', 'TechnoDot Server']} iconpath={[]} {newServer} />
	</Sidebar.Header>
	<Sidebar.Content>
		<Sidebar.Group />
		<Sidebar.Group />
	</Sidebar.Content>
	<Sidebar.Footer>
		<SidebarFooter/>
	</Sidebar.Footer>
</Sidebar.Root>
