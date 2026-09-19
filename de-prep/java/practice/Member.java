package practice;
import java.util.*;

public class Member {
    private long memberId;
    private String name;
    List<String> borrowedIsbns;

    public Member() {}

    public long getMemberId() {
        return memberId;
    }
    public void setMemberId(long memberId) {
        this.memberId = memberId;
    }
    public String getName() {
        return name;
    }
    public void setName(String name) {
        this.name = name;
    }
    public List<String> getBorrowedIsbns() {
        return borrowedIsbns;
    }
    public void setBorrowedIsbns(List<String> borrowedIsbns) {
        this.borrowedIsbns = borrowedIsbns;
    }
    public Member(long memberId, String name, List<String> borrowedIsbns) {
        this.memberId = memberId;
        this.name = name;
        this.borrowedIsbns = borrowedIsbns;
    }
    @Override
    public String toString() {
        return "Member [memberId=" + memberId + ", name=" + name + ", borrowedIsbns=" + borrowedIsbns + "]";
    }

    

}
