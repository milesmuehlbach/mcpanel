<script lang="ts">
	import * as Empty from "$lib/components/ui/empty/index.js";
	import { Button } from "$lib/components/ui/button/index.js";
	import PlusIcon from "@lucide/svelte/icons/plus";
	import ServerIcon from "@lucide/svelte/icons/server";
</script>

<Empty.Root>
	<Empty.Header>
		<Empty.Media variant="icon">
			<ServerIcon />
		</Empty.Media>
		<Empty.Title>No Servers</Empty.Title>
		<Empty.Description>
			You haven't created any servers yet. Start by pressing the below button to make one.
		</Empty.Description>
	</Empty.Header>
	<Empty.Content>
		<div class="flex gap-2">
			<Button class="text-white">Create New Server <PlusIcon class="inline" /></Button>
		</div>
	</Empty.Content>
</Empty.Root>