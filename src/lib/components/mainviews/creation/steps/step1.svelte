<script lang="ts">
	import { Button } from '$lib/components/ui/button';

	let { incrementStep = () => {} }: { incrementStep?: () => void } = $props();
</script>

<div class="flex h-full flex-col justify-center gap-4">
	<h2 class="text-xl font-semibold">Welcome to McPanel</h2>
	<p class="text-sm text-muted-foreground">
		This setup wizard guides you through creating and configuring your first server.
	</p>
	<div>
		<Button type="button" onclick={incrementStep}>Get Started</Button>
	</div>
</div>
