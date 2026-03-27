// place files you want to import through the `$lib` alias in this folder.

export class Instance {
	public name: string;
	public uid: string;

	constructor(name: string, uid: string) {
		this.name = name;
		this.uid = uid;
	}
}