<script>
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import { Separator } from '$lib/components/ui/separator/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import LogOutIcon from '@lucide/svelte/icons/log-out';

	const sidebar = Sidebar.useSidebar();
</script>

<Button
	variant={sidebar.state === 'expanded' ? 'outline' : 'ghost'}
	size="sm"
	class={sidebar.state === 'collapsed' ? 'px-2' : ''}
>
	{#if sidebar.state === 'expanded'}
		Log Out
	{/if}
	<LogOutIcon />
</Button>
<Separator />
<Sidebar.Trigger class="size-8 shrink-0 bg-transparent" />
