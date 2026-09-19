package practice;

public class Book {
    private String title;
    private String author;
    private long isbn;
    private boolean isAvailable;

    public Book(){

    }

    public Book(String title, String author, long isbn, boolean isAvailable)
    {
        this.title = title;
        this.author = author;
        this.isbn = isbn;
        this.isAvailable = isAvailable;
    }

    public void setTitle(String title){
        this.title = title;
    }
    public String getTitle(){
        return this.title;
    }
    public void setAuthor(String author){
        this.author = author;
    }
    public String getAuthor(){
        return this.author;
    }
    public void setIsbn(long isbn){
        this.isbn = isbn;
    }
    public long getIsbn(){
        return this.isbn;
    }
    public void setAvailability(boolean isAvailable){
        this.isAvailable = isAvailable;
    }
    public boolean getAvailability(){
        return this.isAvailable;
    }

    @Override
    public String toString() {
        return "Book [title=" + title + ", author=" + author + ", isbn=" + isbn + ", isAvailable=" + isAvailable + "]";
    }
}
