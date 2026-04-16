<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar';
	import type { Component } from 'svelte';
	import type { IconProps } from '@lucide/svelte';

	let {
		icon: Icon,
		name,
		selected = false
	}: {
		icon: Component<IconProps>;
		name: string;
		selected?: boolean;
	} = $props();
</script>

<Sidebar.MenuItem class="mr-2 ml-2 mt-0.5 md-0.5">
	<Sidebar.MenuButton isActive={selected}>
		<Icon class="mr-2" />
		{name}
	</Sidebar.MenuButton>
</Sidebar.MenuItem>